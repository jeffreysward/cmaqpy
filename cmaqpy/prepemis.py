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
    

def fmt_calc_hourly_base():
    """
    Format the calc_hourly_base.csv file output by the ERTAC EGU preprocessor.
    """
    # Read in the generator data previously preprocessed by ERTAC EGU tool
    base_df = pd.read_csv('ny_calc_hourly_base.csv', low_memory=False)
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
