#/////////////////////////////////////////////////////////////////////////////#

# Script: processing_stopSearch.py

# Required packages:
#import os 
import numpy as np
import pandas as pd


#/////////////////////////////////////////////////////////////////////////////#

def loadSets():
    # Load Datasets 
    data2020 = pd.read_csv('sourceData/ss_open_20.csv')
    data2021 = pd.read_csv('sourceData/ss_open_21.csv')
    data2022 = pd.read_csv('sourceData/ss_open_22.csv')

    # Dictionaries for renaming column headers, 2021 is used for 2022 as well due to the same format.
    headerRename2020 = {'Financial Year':'financialYear','Geocode':'geocode','Force Name':'policeForceArea','Region':'region','Legislation':'legislation','Reason for search / arrest':'reasonForSearch','Ethnic Group (self-defined - new style)':'selfDefinedEthnicityGroup','Ethnicity (self-defined)':'selfDefinedEthnicity','Searches':'numberOfSearches'}
    headerRename2021 = {'financial_year':'financialYear','police_force_area':'policeForceArea','reason_for_search':'reasonForSearch','self_defined_ethnicity_group':'selfDefinedEthnicityGroup','self_defined_ethnicity':'selfDefinedEthnicity','number_of_searches':'numberOfSearches'}

    # Rename 
    data2020.rename(columns=headerRename2020, inplace=True)
    data2021.rename(columns=headerRename2021, inplace=True)
    data2022.rename(columns=headerRename2021, inplace=True)

    # Name places fixing
    data2021['policeForceArea'] = data2021['policeForceArea'].replace('Avon & Somerset','Avon and Somerset')
    data2022['policeForceArea'] = data2022['policeForceArea'].replace('Avon & Somerset','Avon and Somerset')
    data2021['policeForceArea'] = data2021['policeForceArea'].replace('Devon & Cornwall','Devon and Cornwall')
    data2022['policeForceArea'] = data2022['policeForceArea'].replace('Devon & Cornwall','Devon and Cornwall')

    # Name ethnicity fixing
    data2020['selfDefinedEthnicityGroup'] = data2020['selfDefinedEthnicityGroup'].replace('Vehicle only','N/A - vehicle search')
    data2020['selfDefinedEthnicity'] = data2020['selfDefinedEthnicity'].replace('Vehicle only','N/A - vehicle search')

    # Drop tables
    data2020 = data2020[['financialYear','geocode','policeForceArea','region','legislation','reasonForSearch','selfDefinedEthnicityGroup','selfDefinedEthnicity','numberOfSearches']]
    data2021 = data2021[['financialYear','geocode','policeForceArea','region','legislation','reasonForSearch','selfDefinedEthnicityGroup','selfDefinedEthnicity','numberOfSearches']]
    data2022 = data2022[['financialYear','geocode','policeForceArea','region','legislation','reasonForSearch','selfDefinedEthnicityGroup','selfDefinedEthnicity','numberOfSearches']]
    
    # Merging new data sets
    data2021 = data2021.groupby(['policeForceArea','legislation','reasonForSearch','selfDefinedEthnicity','selfDefinedEthnicityGroup'], as_index=False).agg({'numberOfSearches':'sum'})
    data2022 = data2022.groupby(['policeForceArea','legislation','reasonForSearch','selfDefinedEthnicity','selfDefinedEthnicityGroup'], as_index=False).agg({'numberOfSearches':'sum'})
    # Colate Datasets by police force area
    workingData = pd.concat([data2020,data2021,data2022]).sort_values('policeForceArea')

    # Drop BTS
    workingData = workingData[workingData.policeForceArea != "British Transport Police"]

loadSets()


# Notes
# data2020[['Year','Month']] = data2020['Financial Year'].str.split('/',expand=True) Don't need this but it's a nice bit of code so saving for later lol