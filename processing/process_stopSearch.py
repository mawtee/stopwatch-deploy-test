import numpy as np
import pandas as pd


# 0. Function to load and format stop and search data
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
   dfStopSearch = pd.read_csv(r'sourceData/ss_open_'+ str(year) +'.csv')
   
   # Rename columns
   dfStopSearch.rename(columns=colNameDictionary, inplace=True)
   
   # Drop redundant columns
   to_drop = ['Weapons arrests (S60 only)','Other arrests (S60 only)','Persons found to be carrying a weapon (S60 only)']
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
      to_recode = ['outcome', 'numberOfSearches']
      dfStopSearch[to_recode] = dfStopSearch[to_recode].apply(lambda x: x.str.strip())
      dfStopSearch = dfStopSearch.replace({
         'outcome':{'-':'0','*':'0','':'0','..':'0'},
         'numberOfSearches':{'-':'0','*':'0','':'0','..':'0'}})
      dfStopSearch[to_recode] = dfStopSearch[to_recode].astype('int')
      dfStopSearch[to_recode] = np.where(dfStopSearch[to_recode] > 0, 1, 0)
      dfStopSearch['outcome'] = np.where(
         dfStopSearch['outcome'] == 0, "No Arrest", "Arrest").astype("str")
      
   else:
      dfStopSearch['outcome'] = np.where(
        dfStopSearch['outcome'] != "Arrest", "No Arrest", "Arrest")

   # Summarise data to match 2020 aggregation
   if year > 2020:
      dfStopSearch = dfStopSearch.groupby(['pfaName','legislation','reasonForSearch','selfDefinedEthnicity','selfDefinedEthnicityGroup'], as_index=False).agg({'numberOfSearches':'sum'})
   
   # Year indicator (and dropping redundant years (pre-2011) for 2020 historica data)
   if year == 2020:
      dfStopSearch['year'] =  dfStopSearch['financialYear'].str[:4].astype('int')
      dfStopSearch = dfStopSearch[dfStopSearch['year'] >= 2011]  
   else:
      yearMinus1 = year - 1
      dfStopSearch['year'] = yearMinus1
      dfStopSearch['financialYear'] = ""+str(yearMinus1)+"/" + str(year)
      
   return dfStopSearch

# Notes
# data2020[['Year','Month']] = data2020['Financial Year'].str.split('/',expand=True) Don't need this but it's a nice bit of code so saving for later lol