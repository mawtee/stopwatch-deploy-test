import numpy as np
import pandas as pd

#==============================================================================
#                             0. Stop and Search data                         #                                
#==============================================================================


# 0.0. Function to load and format stop and search data
#=======================================================

def process_stop_search(year, colNameDictionary):
  
   """
   Description: 
      Loads stop and search data for each year specified in global 
      option - 'YEARS_SS'- and then cleans and transforms the data into 
      required format.
     
   Inputs:
      'year' - the year (or a list of years) corresponding to the publication year 
      of each the stop and search dataset(s) [download from https://www.gov.uk/government/statistics/police-powers-and-procedures-stop-and-search-and-arrests-england-and-wales-year-ending-31-march-2022]
  
   Returns:
      'dfStopSearch' - a formatted dataframe for stop and search statistics
       corresponding to the input year
   """
          
   # Load 
   print("Loading and formatting "+ str(year) +" stop and search data")
   dfStopSearch = pd.read_csv('sourceData/ss_open_'+ str(year) +'.csv')
   
   # Rename columns
   dfStopSearch.rename(columns=colNameDictionary, inplace=True)
   
   # Drop redundant columns
   to_drop = ['Weapons arrests (S60 only)','Other arrests (S60 only)','Persons found to be carrying a weapon (S60 only)', 'Ethnic Group (self-defined - old style)', 'outcome']
   dfStopSearch.drop(columns=[col for col in dfStopSearch if col in to_drop], inplace = True)
   
   # Homogenise Police Force Area names
   dfStopSearch['pfaName'] = dfStopSearch['pfaName'].replace(
      {'Avon & Somerset':'Avon and Somerset', 
       'Devon & Cornwall':'Devon and Cornwall'})
   
   # Homogenise (and recode) ethnicity group categories
   ethnicityGroupMap = {'Black or Black British':'Black', 
                        'Asian or Asian British':'Asian',
                        'N/A - vehicle search':'Not Stated / Unknown',  
                        'Vehicle only':'Not Stated / Unknown', 
                        'Not stated':'Not Stated / Unknown',
                        'Not Stated':'Not Stated / Unknown'
                        }
   dfStopSearch = dfStopSearch.replace({
      'selfDefinedEthnicityGroup': ethnicityGroupMap})
   
   # Recode outcomes
   if year == 2020:
      to_recode = ['numberOfSearches']
      dfStopSearch[to_recode] = dfStopSearch[to_recode].apply(lambda x: x.str.strip())
      dfStopSearch = dfStopSearch.replace({
         'numberOfSearches':{'-':'0','*':'0','':'0','..':'0'}})
      dfStopSearch[to_recode] = dfStopSearch[to_recode].astype('int')
      
   # Summarise data to match 2020 aggregation
   if year > 2020:
      dfStopSearch = dfStopSearch.groupby(['pfaName', 'pfaCode', 'legislation', 'region', 'reasonForSearch','selfDefinedEthnicity','selfDefinedEthnicityGroup'], as_index=False).agg({'numberOfSearches':'sum'})
   
   # Year indicator (and dropping redundant years (pre-2011) for 2020 historica data)
   if year == 2020:
      dfStopSearch['year'] =  dfStopSearch['financialYear'].str[:4].astype('int')
      dfStopSearch = dfStopSearch[dfStopSearch['year'] >= 2011]  
   else:
      yearMinus1 = year - 1
      dfStopSearch['year'] = yearMinus1
      dfStopSearch['financialYear'] = ""+str(yearMinus1)+"/" + str(year)
      
   return dfStopSearch


#==============================================================================
#                             1. Census data                                  #                                
#==============================================================================

# 1.0 Function to load and format census data
#=======================================================

def load_and_format_census(year, nskip, colnames):
    
   """
   Description: 
      Loads, cleans and aggregates Local Authority (LA) ethnnic group census population counts 
      to the level of Police Force Area (PFA).
     
   Inputs:
      'year' - The year (or a list of years) corresponding to the publication year 
      of the census dataset(s) [download from ]
      'nskip' - A list of numbers denoting the number of rows to skip when loading data
      'colnames' - A list of column name lists giving the name of the columns for each dataframe
      
   Returns:
      'dfCensusLA' - a formatted dataframe for ethnicity census data at LA level and
      corresponding to the input year
   """

   #; Load census data
   print("Loading and aggregating "+ str(year) +" census data")
   dfCensusLA = pd.read_csv('sourceData/'+ str(year) +'_census_la.csv', skiprows=nskip)

   #; Rename columns
   dfCensusLA.columns = colnames
    
   #; Drop Wales LAs
   #dfCensusLA = dfCensusLA[dfCensusLA["laCode"].str.contains("W") == False]
    
   #; Reshape 2011 ethnicity columns from wide to long (and de-string ethnic group values)
   if year == 2011:
      dfCensusLA = pd.melt(dfCensusLA, id_vars = ['laCode', 'laName'],
                           var_name = 'ethnicGroupCode', value_name = 'count')
      dfCensusLA['ethnicGroupCode'] = dfCensusLA['ethnicGroupCode'].str.replace('v_', '').astype(int)

   #; Create broad ethnic groupings
   #...one less white category in 2021 data, hence adjustment
   ethnicGroups = ["Asian", "Black", "Mixed", "White", "Other Ethnic Group"]
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
   dfCensusLA['selfDefinedEthnicityGroup'] = np.select(groupCond, ethnicGroups, np.nan)
   
   # Drop redundant column
   dfCensusLA.drop([col for col in dfCensusLA.columns if 'ethnicGroupName' in col],axis=1,inplace=True)
   
   return dfCensusLA
 
   
# 1.1 Function to aggregate census data to from LA to PFA
#=======================================================

def aggregate_census_PFA_to_LA(dfCensusLA, year):
   
   """
   Description: 
      Aggregates census data from LA to PFA level using LA-PFA lookup table.
     
   Inputs:
      'dfCensusLA' - A formatted dataframe for LA census data correspdoning
      to the input year
      'year' - The year (or a list of years) corresponding to the publication year 
      of the census dataset(s)
   Returns:
      'dfCensusPFA' - a formatted dataframe for ethnicity census data at PFA level and
      corresponding to the input year
   """
    
   #; Aggregate (sum) population count for broad ethnic groups
   dfCensusLA = dfCensusLA.groupby(
      ['laCode', 'selfDefinedEthnicityGroup'])['count'].sum().reset_index()
   print("Population count for NaN observations in " + str(year) + " = " +
         str(dfCensusLA.loc[dfCensusLA['selfDefinedEthnicityGroup'] == np.nan, 'count'].sum()))

   #; Drop NaN observations 
   dfCensusLA = dfCensusLA.replace('nan', np.NaN).dropna(
      subset = ['selfDefinedEthnicityGroup'], how = 'any', axis=0)
   dfCensusLA = dfCensusLA[dfCensusLA['laCode'].str.contains('geographic|geographies')==False]
   
   
   #; Lookup 2021 LA codes for 2011 LA census data via merge (keep Wales 2013 due to unavailability of 2013-2021 lookup keys for Wales)
   if year == 2011:
      dfLookupLA = pd.read_csv('sourceData\la11_la21_lookup.csv',skiprows = 2, header = 0,
                               usecols=['Local Authority District Area 2013 Code', 
                                        'Local Authority District Area 2021 Code'])
      dfCensusLA = pd.merge(dfCensusLA, dfLookupLA, left_on = 'laCode', right_on = 'Local Authority District Area 2013 Code', how='outer')
     
      dfCensusLA['Local Authority District Area 2021 Code'] = np.where(dfCensusLA['laCode'].str.startswith('W'), dfCensusLA['laCode'], dfCensusLA['Local Authority District Area 2021 Code'])
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
      ['pfaCode', 'pfaName', 'selfDefinedEthnicityGroup'])['count'].sum().reset_index()
       
   #; Check number of PFAs
   print("Total number of PFAs in " + str(year) + " data = "+ str(dfCensusPFA['pfaCode'].nunique()))
   
   #; Year indicator
   dfCensusPFA['year'] = year
   
   return dfCensusPFA


# 1.2 Function to expand dataset for full time series
#=======================================================

def expand_census(dfCensusPFA):
    
   """
   Description: 
      Expands LA census data into a yearly 2011-2021 time series.
     
   Inputs:
      'dfCensusPFA' - a formatted dataframe for ethnicity census data at 
      PFA level andcorresponding to the input year
   Returns:
      'dfCensusPFAseries' - a formatted timeseries dataframe for ethnicity census data
      at PFA level 
   """

   # Reshape ethnicity column from long to wide
   dfCensusPFA = pd.pivot(dfCensusPFA, index = ['pfaCode', 'pfaName', 'year'],
                          columns = 'selfDefinedEthnicityGroup', values = 'count')
   dfCensusPFA = dfCensusPFA.reset_index()

   # Expand dataframe 6 times (6*2) to create observations required for yearly time series
   dfCensusPFAseries = pd.concat([dfCensusPFA]*6, ignore_index = True) 

   # Reset ethnicity population counts to NA for all but the first (2011) and last (2021) years
   dfCensusPFAseries = dfCensusPFAseries.sort_values(by = ['pfaCode', 'year'])
   dfCensusPFAseries['cumCount'] = dfCensusPFAseries.groupby('pfaCode').cumcount()+1
   
   ethnicGroups = ["Asian", "Black", "Mixed", "White", "Other Ethnic Group"]
   dfCensusPFAseries.loc[dfCensusPFAseries.cumCount.isin(range(2,11)), ethnicGroups] = np.nan

   # Drop 12th replication to get required number of years (11)
   dfCensusPFAseries = dfCensusPFAseries[dfCensusPFAseries.cumCount != 12]

   # Recode year column as sequential time series
   yearMap = {1:2011, 2:2012, 3:2013, 4:2014, 5:2015, 
              6:2016, 7:2017, 8:2018, 9:2019, 10:2020, 11:2021}
   dfCensusPFAseries = dfCensusPFAseries.assign(
     year = dfCensusPFAseries.cumCount.map(yearMap))
   
   return dfCensusPFAseries


# 1.3 Function to interpolate non-census years
#=======================================================

def fill_and_interpolate_census(dfCensusPFAseries):
    
   """
   Description: 
      Employs a), forward filling and b), linear interpolation to estimate population counts for non-census years (2012-2020).
     
   Inputs:
      'dfCensusPFAseries' - a formatted timeseries dataframe for ethnicity census data
      at PFA level 
   Returns:
      'dfCensusPFAseriesFillIpol' - a formatted timeseries dataframe for ethnicity census data
      at PFA level with forward filled and linearly interpolated population estimates
   """
   
   # Forward fill
   dfCensusPFAseriesFill = dfCensusPFAseries.fillna(method='ffill')
   dfCensusPFAseriesFill.drop(columns = 'cumCount', inplace = True)
   dfCensusPFAseriesFill = pd.melt(
      dfCensusPFAseriesFill, id_vars = ['pfaCode', 'pfaName', 'year'],
      var_name = 'selfDefinedEthnicityGroup', value_name = 'population')
   dfCensusPFAseriesFill['population'] = round(
      dfCensusPFAseriesFill['population'], 0)
   
   # Linear interpolation 
   ethnicGroups = ["Asian", "Black", "Mixed", "White", "Other Ethnic Group"]
   dfCensusPFAseries[ethnicGroups] = dfCensusPFAseries[
      ['pfaCode', 'pfaName', 'year', "Asian", 
       'Black', "Mixed", "White", "Other Ethnic Group"]].groupby(
          'pfaCode', group_keys = False).apply(
             lambda x:x).interpolate(method='linear')[ethnicGroups]
   dfCensusPFAseries.drop(columns = 'cumCount', inplace = True)
   dfCensusPFAseriesIpol = pd.melt(
      dfCensusPFAseries, id_vars = ['pfaCode', 'pfaName', 'year'],
      var_name = 'selfDefinedEthnicityGroup', value_name = 'populationIpol')
   dfCensusPFAseriesIpol['populationIpol'] = round(
      dfCensusPFAseriesIpol['populationIpol'], 0)
   
   # Merge
   dfCensusPFAseriesFillIpol = dfCensusPFAseriesFill
   dfCensusPFAseriesFillIpol['populationIpol'] =  dfCensusPFAseriesIpol['populationIpol']
   
   return dfCensusPFAseriesFillIpol


# 1.3 Function to merge stop-search and census data
#=======================================================

def merge_ss_census(dfStopSearchPFA, dfCensusPFAseriesFillIpol):
    
   """
   Description: 
      Merges stop-search tables with census data and drop redundant PFAs (BTP and London, City of)
     
   Inputs:
      'dfStopSearchPFA' - a formatted timeseries dataframe of stop and searcg data at PFA level
      'dfCensusPFAseriesFillIpol' -  a formatted timeseries dataframe for ethnicity census data at PFA level
   Returns:
      'dfPFA' - a formatted timeseries dataframe for stop-search and ethnicity data used as main input for PFA-level analysis
   """
   
   dfPFA = pd.merge(dfStopSearchPFA, dfCensusPFAseriesFillIpol[['pfaName', 'year', 'selfDefinedEthnicityGroup', 'population', 'populationIpol']], 
                 on = ['pfaName', 'year', 'selfDefinedEthnicityGroup'], how = 'left')
   dfPFA = dfPFA[dfPFA['selfDefinedEthnicityGroup'] != 'Not Stated / Unknown']
   dfPFA = dfPFA[dfPFA['pfaName'] != 'British Transport Police']
   dfPFA = dfPFA[dfPFA['pfaName'] != 'London, City of']
   
   return dfPFA



   
      
