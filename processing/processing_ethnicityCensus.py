#/////////////////////////////////////////////////////////////////////////////#

# Script: processing_ethnicityCensus.py

# Required packages:
#import os 
import numpy as np
import pandas as pd


#/////////////////////////////////////////////////////////////////////////////#


# 1.2 Formatting census data for analysis
# =========================================

### Global ethnic groups vector
ethnicGroups = ["Asian", "Black", "Mixed", "White", "Other"]


#### Function to load and clean census data
def load_and_clean(year, nskip, colnames):
    
    # Description
    """Loads, cleans and aggregates Local Authority (LA) ethnnic group census population counts 
       to the level of Police Force Area (PFA)."""
    
    #; Load census data
    print("Loading and aggregating "+ str(year) +" census data")
    dfCensusLA = pd.read_csv('sourceData/'+ str(year) +'_census_la.csv',  skiprows=nskip)

    #; Rename columns
    dfCensusLA.columns = colnames
    
    #; Drop Wales LAs
    dfCensusLA = dfCensusLA[dfCensusLA["laCode"].str.contains("W") == False]
    
    #; Reshape 2011 ethnicity columns from wide to long (and de-string ethnic group values)
    if year == 2011:
      dfCensusLA = pd.melt(dfCensusLA, id_vars = ['laCode', 'laName'],
                           var_name = 'ethnicGroupCode', value_name = 'count')
      dfCensusLA['ethnicGroupCode'] = dfCensusLA['ethnicGroupCode'].str.replace('v_', '').astype(int)

    #; Create broad ethnic groupings
    #...one less white category in 2021 data, hence adjustment
    asianGroup = range(1, 6)
    blackGroup = range(6, 9)
    mixedGroup = range(9, 13)
    if year == 2011:
       whiteGroup = range(13, 17) 
       otherGroup = range(17,19) 
    elif year == 2021:
      whiteGroup = range(13, 18) 
      otherGroup = range(18, 20) 
    groupCond = [dfCensusLA.ethnicGroupCode.isin(asianGroup),
                 dfCensusLA.ethnicGroupCode.isin(blackGroup),
                 dfCensusLA.ethnicGroupCode.isin(mixedGroup),
                 dfCensusLA.ethnicGroupCode.isin(whiteGroup),
                 dfCensusLA.ethnicGroupCode.isin(otherGroup)]
    dfCensusLA['ethnicGroupBroad'] = np.select(groupCond, ethnicGroups, np.nan)
    
    return dfCensusLA


### Function to aggregate census data to PFA
def aggregate(dfCensusLA, year):
    
    #; Aggregate (sum) population count for broad ethnic groups
    dfCensusLA = dfCensusLA.groupby(
      ['laCode', 'ethnicGroupBroad'])['count'].sum().reset_index()
    print("Population count for NaN observations in " + str(year) + " = " +
          str(dfCensusLA.loc[dfCensusLA['ethnicGroupBroad'] == np.nan, 'count'].sum()))

    #; Drop NaN observations 
    dfCensusLA = dfCensusLA.replace('nan', np.NaN).dropna(
      subset = ['ethnicGroupBroad'], how = 'any', axis=0)
    
    #; Lookup 2021 LA codes for 2011 LA census data via merge
    if year == 2011:
      dfLookupLA = pd.read_csv('sourceData\la11_la21_lookup.csv',skiprows = 2, header = 0,
                               usecols=['Local Authority District Area 2013 Code', 
                                        'Local Authority District Area 2021 Code'])
      dfCensusLA = pd.merge(dfCensusLA, dfLookupLA, 
                            left_on = 'laCode', right_on = 'Local Authority District Area 2013 Code')
      dfCensusLA.drop(['laCode', 'Local Authority District Area 2013 Code'],
                      axis = 1, inplace = True)
      dfCensusLA.rename(columns = {
        'Local Authority District Area 2021 Code':'laCode'}, inplace = True)
      
    #; Check number of LAs
    print("Total number of LAs in " + str(year) + " data = " + str(dfCensusLA['laCode'].nunique()))

    #; Load LA to PFA lookup
    dfLookupPFA = pd.read_csv('sourceData\la_pfa_lookup.csv')

    #; Drop redundant columns and rename
    dfLookupPFA = dfLookupPFA.drop(['CSP21CD', 'CSP21NM', 'LAD21NM'], axis=1)
    dfLookupPFA.columns = ['laCode', 'pfaCode', 'pfaName']

    #; Merge with census data
    dfCensusPFA = pd.merge(dfCensusLA, dfLookupPFA, on = 'laCode')

    #; Aggregate (sum) population count for PFA by broad ethnic group
    dfCensusPFA = dfCensusPFA.groupby(
      ['pfaCode', 'pfaName', 'ethnicGroupBroad'])['count'].sum().reset_index()
        
    #; Check number of PFAs
    print("Total number of PFAs in " + str(year) + " data = "+ str(dfCensusPFA['pfaCode'].nunique()))
    
    #; Year indicator
    dfCensusPFA['year'] = year
    
    #; Return dataframe to list
    return dfCensusPFA


### Function to expand dataset for full time series
def expand(dfCensusPFA):
    
    # Description
    """Expands census data into a yearly 2011-2021 time series"""
    
    # Reshape ethnicity column from long to wide
    dfCensusPFA = pd.pivot(dfCensusPFA, index = ['pfaCode', 'pfaName', 'year'],
                               columns = 'ethnicGroupBroad', values = 'count')
    dfCensusPFA = dfCensusPFA.reset_index()

    # Expand dataframe 6 times (6*2) to create observations required for yearly time series
    dfCensusPFAseries = pd.concat([dfCensusPFA]*6, ignore_index = True) 

    # Reset ethnicity population counts to NA for all but the first (2011) and last (2021) years
    dfCensusPFAseries = dfCensusPFAseries.sort_values(by = ['pfaCode', 'year'])
    dfCensusPFAseries['cumCount'] = dfCensusPFAseries.groupby('pfaCode').cumcount()+1
    dfCensusPFAseries.loc[dfCensusPFAseries.cumCount.isin(range(2,11)), ethnicGroups] = np.nan

    # Drop 12th replication to get required number of years (11)
    dfCensusPFAseries = dfCensusPFAseries[dfCensusPFAseries.cumCount != 12]

    # Recode year column as sequential time series
    yearMap = {1:2011, 2:2012, 3:2013, 4:2014, 5:2015, 
               6:2016, 7:2017, 8:2018, 9:2019, 10:2020, 11:2021}
    dfCensusPFAseries = dfCensusPFAseries.assign(
      year = dfCensusPFAseries.cumCount.map(yearMap))
    
    return dfCensusPFAseries


### Function to interpolate non-census years
def interpolate(dfCensusPFAseries):
    
    # Description
    """Employs linear interpolation to estimate population counts for non-census years (2012-2020)."""
    
    # Linear interpolation 
    ethnicGroupsLow= []
    for g in ethnicGroups:
      ethnicGroupsLow.append(g.lower())
    dfCensusPFAseries[ethnicGroupsLow] = dfCensusPFAseries[
      ['pfaCode', 'pfaName', 'year', "Asian", 
       "Black", "Mixed", "White", "Other"]].groupby(
         'pfaCode', group_keys = False).apply(
            lambda x:x).interpolate(method='linear')[ethnicGroups]
           
    # Drop redundant columns
    todrop = []      
    todrop.extend(ethnicGroups + ['cumCount'])   
    dfCensusPFAseries.drop(columns = todrop, inplace = True)

    # Add population suffix to ethnicity column names 
    dfCensusPFAseriesIpol = dfCensusPFAseries.rename(
      columns={g: g+'Pop' for g in dfCensusPFAseries.columns if g in ethnicGroupsLow})
    
    # Return 
    return dfCensusPFAseriesIpol


### Main function to format census data for analysis
def format_census():
    
    # Description
    """Ingests 2011 and 2021 LA ethnicity census data and outputs a yearly 2011-2021 time series 
       at PFA level using linear interpolation to estimate population counts for non-census years (2012-2020).
       The functions used are 'load_and_clean', 'aggregate', 'expand' and 'interpolate''."""

    # Creating vectors to store years, rows to skip and 
    # column names for each run of 'load_and_aggregate' function
    years = [2011, 2021]
    nskip = [8,0]                                                                      
    colnames0 = []      
    colnames0.extend(['laName', 'laCode'] + ['v_' + str(i) for i in range(1,19)])   
    colnames1 = ['laCode', 'laName', 'ethnicGroupCode', 'ethnicGroupName', 'count'] 
    colnames = [colnames0, colnames1] 
    
    # Empty list to store yearly dataframes 
    dfCensusPFA_list = []
    
    # Run the following for each year 
    for i in range(len(years)):
      # Load and clean census data
      df = load_and_clean(years[i], nskip[i], colnames[i])
      # Aggregate census data from LA to PFA
      df = aggregate(df, years[i])
      # Append census data list
      dfCensusPFA_list.append(df)
      
    # Unlist census data and append years into single dataframe
    dfCensusPFA = pd.concat(dfCensusPFA_list, ignore_index=True)
    
    # Expand and interpolate to create full time series:
    dfCensusPFAseries = expand(dfCensusPFA)
    dfCensusPFAseriesIpol = interpolate(dfCensusPFAseries)
    
    # Return time series
    return dfCensusPFAseriesIpol



format_census()




#### Some random shit - can't figure out how to import script into iPython console
### so that I can inspect dataframe as Spyder object/variable f
#if __name__ == "__main__": 
# import scriptname
# format census()

    
    
    
    

    