"""
Functions to help prepare emissions for CMAQ.
"""

import pandas as pd

def fmt_like_camd(data_file='./pred_xg_co2.csv', lu_file='./RGGI_to_NYISO.csv'):
    """
    Takes data output from either the NY Simple Net or the ML Emissions Estimator, 
    and formats it for input into CAMD.
    """
    # Read in data 
    raw_data_df = pd.read_csv(data_file, parse_dates=['TimeStamp'], infer_datetime_format=True)
    raw_data_df = raw_data_df.set_index('TimeStamp')
    # Read the lookup file
    lu_df = pd.read_csv(lu_file, header=1)
    lu_df = lu_df.drop(columns=['Notes', 'Unnamed: 6'])
    # Drop unnecessary units from the lookup df
    fmt_data_df = lu_df[lu_df['NYISO Name'].isin(raw_data_df.columns)].reset_index(drop=True)
    # Format the final dataset
    fmt_data_df = pd.concat([fmt_data_df, pd.DataFrame(index=fmt_data_df.index, columns=raw_data_df.index.values)], axis=1)
    # Create a generation dataframe for each ORISPL, UNIT ID combination
    for name in fmt_data_df['NYISO Name']:
        # Get simple net generation 
        unit_data = raw_data_df[name]
        # Determine how many units are associated with this name
        unit_bool = fmt_data_df['NYISO Name'] == name
        n_units = sum(unit_bool)
        # Edit the simple net generation based on this number of units
        unit_data = unit_data / n_units
        # Fill this unit gen profile into all matching units
        for idx in unit_bool[unit_bool].index.values:
            fmt_data_df.loc[idx, unit_data.index] = unit_data

    # Change the ORISPL to a string
    fmt_data_df = fmt_data_df.astype({'ORISPL': 'int'})
    fmt_data_df = fmt_data_df.astype({'ORISPL': 'str'})

    return fmt_data_df
    

def fmt_calc_hourly_base(base_file='calc_hourly_base.csv'):
    """
    Format the calc_hourly_base.csv file output by the ERTAC EGU preprocessor.
    """
    # Read in the generator data previously preprocessed by ERTAC EGU tool
    base_df = pd.read_csv(base_file, low_memory=False)
    # Change op_hour to str
    base_df = base_df.astype({'op_hour': 'str'})
    # Change the orispl_code to a string
    base_df = base_df.astype({'orispl_code': 'int'})
    base_df = base_df.astype({'orispl_code': 'str'})
    # Pad the string for formatting
    base_df['op_hour'] = base_df['op_hour'].str.zfill(2)
    # Add a datetime column 
    base_df['datetime'] = pd.to_datetime(base_df['op_date'] + ' ' + base_df['op_hour'])

    return base_df


def update_camd(in_emis_file='calc_hourly_base.csv', co2_file='pred_xg_co2.csv', 
                nox_file='pred_xg_nox.csv', so2_file='pred_xg_so2.csv', 
                gen_file='pred_xg_so2.csv', lu_file='RGGI_to_NYISO.csv', 
                out_emis_file='Updated_calc_hourly_base.csv'):
    """
    Update the CAMD load and emissions data with that generated from the NY Simple Net 
    and the ML-based emissions estimates. 
    """
    # Read in the base emissions file
    base_df = fmt_calc_hourly_base(base_file=in_emis_file)
    # Read in ML CO2 emissions estimations
    ml_co2 = fmt_like_camd(data_file=co2_file, lu_file=lu_file)
    # Read in ML NOx emissions estimations
    ml_nox = fmt_like_camd(data_file=nox_file, lu_file=lu_file)
    # Read in ML SO2 emissions estimations
    ml_so2 = fmt_like_camd(data_file=so2_file, lu_file=lu_file)
    # Read in NY Simple Net generation
    ed_gen = fmt_like_camd(data_file=gen_file, lu_file=lu_file)
    
    # Get the name of an individual EGU -- this is how units are identified in the NY Simple Net & the ML
    for idx in ml_co2.index:
        # Get the ORISPL and the Unit ID
        egu_orispl = ml_co2.loc[idx].ORISPL
        egu_unitid = ml_co2.loc[idx]['Unit ID']
        print(f'Working on ORISPL: {egu_orispl}\tUNIT ID:{egu_unitid}')

        # Extract this ORISPL and UNIT ID from the base DataFrame
        egu_df = base_df.loc[(base_df['orispl_code'] == egu_orispl) & (base_df['unitid'] == egu_unitid)]
        # Extract the correct time window
        egu_df = egu_df.loc[base_df['datetime'].isin(ml_co2.columns[5:])]
        if len(egu_df) == 0:
            print('Warning: this unit was not found in the CAMD data.')
        
        # Replace the CO2 emissions values
        # NOTE: this is probably a dangerous way of doing this -- might be better to add the datetime as another index in the egu_df
        egu_df['co2_mass (tons)'] = ml_co2.loc[idx, ml_co2.columns[5:]].values
        # Replace the SO2 emissions values
        egu_df['so2_mass (lbs)'] = ml_so2.loc[idx, ml_co2.columns[5:]].values
        # Replace the NOx emissions values
        egu_df['nox_mass (lbs)'] = ml_nox.loc[idx, ml_co2.columns[5:]].values
        # Replace the load values
        egu_df['gload (MW-hr)'] = ed_gen.loc[idx, ml_co2.columns[5:]].values
        # Combine this new unit data back into the base_df
        base_df.update(egu_df)

    # Save the updated emissions to a new CSV
    base_df.to_csv(out_emis_file)     
