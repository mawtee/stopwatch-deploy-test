import sys
sys.path.append("./processing")
from processing.process_data import *  # NOQA
import numpy as np # NOQA
import pandas as pd


#==============================================================================
#                             0. Global options                               #                                
#==============================================================================


# 0.1 Stop and search data processing options
#---------------------------------------------

# A list of years (inset additional year for new data)
YEARS_SS = [2020, 2021, 2022]

# A list of column name dictionaries (insert additional dictionaries if additional year)
COL_NAME_DICTIONARY_LIST_SS = [
   {'Financial Year':'financialYear','Geocode':'pfaCode','Force Name':'pfaName','Region':'region','Legislation':'legislation','Reason for search / arrest':'reasonForSearch','Ethnic Group (self-defined - new style)':'selfDefinedEthnicityGroup','Ethnicity (self-defined)':'selfDefinedEthnicity','Searches':'numberOfSearches', 'Resultant arrests':'outcome'},
   {'financial_year':'financialYear','Geocode':'pfaCode','police_force_area':'pfaName','reason_for_search':'reasonForSearch','self_defined_ethnicity_group':'selfDefinedEthnicityGroup','self_defined_ethnicity':'selfDefinedEthnicity','number_of_searches':'numberOfSearches'},
   {'financial_year':'financialYear','Geocode':'pfaCode','police_force_area':'pfaName','reason_for_search':'reasonForSearch','self_defined_ethnicity_group':'selfDefinedEthnicityGroup','self_defined_ethnicity':'selfDefinedEthnicity','number_of_searches':'numberOfSearches'}
  ]

# 0.2. Census data processing options
#-------------------------------------

# A list of years (inset additional year for new data)
YEARS_CENSUS = [2011, 2021]

# A list of numbers denoting the number of rows to skip when loading data (insert additional input if additional year)
NSKIP_CENSUS = [8,0]  

# A list of column name lists (create additional list and add to list of lists (COLNAMES_CENSUS) if additional year)                                                                    
COLNAMES0_CENSUS = []      
COLNAMES0_CENSUS.extend(['laName', 'laCode'] + ['v_' + str(i) for i in range(1,19)])   
COLNAMES1_CENSUS = ['laCode', 'laName', 'ethnicGroupCode', 'ethnicGroupName', 'count'] 
COLNAMES_CENSUS = [COLNAMES0_CENSUS, COLNAMES1_CENSUS] 


#==============================================================================
#                              1. Processing data                             #                                
#==============================================================================

# 1.1 Process stop and search data
#------------------------------------

dfStopSearchPFA_list = []
for y in range(len(YEARS_SS)):
   df = process_stop_search(YEARS_SS[y], COL_NAME_DICTIONARY_LIST_SS[y]) 
   dfStopSearchPFA_list.append(df)
dfStopSearchPFA= pd.concat(dfStopSearchPFA_list, ignore_index=True)


# 1.2. Process census data
#---------------------------

dfCensusPFA_list = []
for y in range(len(YEARS_CENSUS)):
   df = load_and_format_census(YEARS_CENSUS[y], NSKIP_CENSUS[y], COLNAMES_CENSUS[y])
   df = aggregate_census_PFA_to_LA(df, YEARS_CENSUS[y])
   dfCensusPFA_list.append(df)
dfCensusPFA = pd.concat(dfCensusPFA_list, ignore_index=True)
dfCensusPFAseries = expand_census(dfCensusPFA)
dfCensusPFAseriesIpol = interpolate_census(dfCensusPFAseries)

# 1.3. Merge stop and search and census data
#----------------------------------------------
dfPFA = pd.merge(dfStopSearchPFA, dfCensusPFAseriesIpol[ ['pfaCode', 'year', 'selfDefinedEthnicityGroup', 'population']], 
              on = ['pfaCode', 'year', 'selfDefinedEthnicityGroup'], how = 'left')







