#import sys
#sys.path.append("./processing")
from process_data_fns import *  # NOQA
import numpy as np # NOQA
import pandas as pd
import random as rnd
import geopandas as gpd
import panel as pn
import panel_highcharts as ph
import pydeck as pdk
ph.config.theme(name="high-contrast-dark")
pn.extension("highchart", template="fast", sizing_mode="stretch_width")
pn.extension('deckgl')



#==============================================================================
#                             0. Global options                               #                                
#==============================================================================


# 0.1 Stop and search data processing options
#---------------------------------------------

# A list of years (insert additional year for new data)
# Note that 2020 refers to historical stop and search data, starting in 2011 and ending in 2020
YEARS_SS = [2020, 2021, 2022]

# A list of column name dictionaries 
# Insert additional dictionary below if additional year; this should (but may not necessarily) take the exact same format as earlier year(s)
COL_NAME_DICTIONARY_LIST_SS = [
   {'Financial Year':'financialYear','Geocode':'pfaCode','Force Name':'pfaName','Region':'region','Legislation':'legislation','Reason for search / arrest':'reasonForSearch','Ethnic Group (self-defined - new style)':'selfDefinedEthnicityGroup','Ethnicity (self-defined)':'selfDefinedEthnicity','Searches':'numberOfSearches', 'Resultant arrests':'outcome'},
   {'financial_year':'financialYear','geocode':'pfaCode','police_force_area':'pfaName', 'region':'region', 'legislation':'legislation', 'reason_for_search':'reasonForSearch', 'self_defined_ethnicity_group':'selfDefinedEthnicityGroup','self_defined_ethnicity':'selfDefinedEthnicity','number_of_searches':'numberOfSearches'},
   {'financial_year':'financialYear','geocode':'pfaCode','police_force_area':'pfaName', 'region':'region', 'legislation':'legislation', 'reason_for_search':'reasonForSearch', 'self_defined_ethnicity_group':'selfDefinedEthnicityGroup','self_defined_ethnicity':'selfDefinedEthnicity','number_of_searches':'numberOfSearches'}
  ]

# 0.2. Census data processing options
#-------------------------------------

# A list of years (inset additional year for new data)
# At the time of writing, the ONS does not publish yearly population estimates by ethnicity and so the next publication year is assumed to be 2031
YEARS_CENSUS = [2011, 2021]

# A list of numbers denoting the number of rows to skip  when loading census data (insert additional input if additional year)
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
dfCensusPFAseriesFillIpol = fill_and_interpolate_census(dfCensusPFAseries)

# 1.3. Merge stop and search and census data
#----------------------------------------------

dfPFA = merge_ss_census(dfStopSearchPFA, dfCensusPFAseriesFillIpol)
dfPFA.to_csv(r"C:\Users\Matt\Downloads\dfPFA_clean.csv")


#==============================================================================
#                              2. App                                         #                                
#==============================================================================

# Loading Data
#dfPFA = pd.read_csv('dfPFA_clean.csv')
dfPFA = pd.read_csv(r"C:\Users\Matt\Git\StopWatch\sourceData\dfPFA_clean.csv", low_memory=False)
boundsPFA = gpd.read_file(r"C:\Users\Matt\Git\StopWatch\sourceData\pfa_merged_bounds_sm2.geojson")


#================================================================================================
#                                         1. Sidebar widgets                                    #                                
#================================================================================================

# 1.0. Year range slider
#--------------------------
startYear = dfPFA.year.min().astype('int').item()
endYear = dfPFA.year.max().astype('int').item()
year_ops = pn.widgets.IntRangeSlider(
    name='What year(s) would like to visualise?',
    start=startYear, end=endYear, 
    value=(startYear, endYear), value_throttled=(startYear, endYear),
    step=1, bar_color = '#E10000')

# 1.1. PFA area drop down list
#---------------------------------
pfaName_list = dfPFA.pfaName.unique().tolist()
pfaName_ops = pn.widgets.Select(name='What Police Force Area (PFA) would you like to visualise?', options=pfaName_list)

# 1.2. Legislation drop down list
#-----------------------------------
legislation_list = dfPFA.legislation.unique().tolist()
legislation_ops = pn.widgets.Select(name='Which legislation would like to visualise?', options=legislation_list)


population_list = ['Unadjusted', 'Adjusted']
population_ops = pn.widgets.Select(name='Which legislation would like to visualise?', options=legislation_list)

#==================================================================================================
#                                    2. Options based dataframes                                  #
#==================================================================================================

# 2.0.0 Aggregate dataframe for selected PFA
#-----------------------------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops)
def create_dfPFA_ops_agg(dfPFA, year_ops, pfaName_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['pfaName'] == pfaName_ops]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
   dfPFA_ops_agg = dfPFA_ops.groupby(['pfaName', 'legislation'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   return dfPFA_ops_agg

# 2.0.1 Aggregate time-series dataframe for selected PFA
#-----------------------------------------------
@pn.depends(year_ops,pfaName_ops,legislation_ops)
def create_dfPFA_ops_agg_ts(dfPFA, year_ops, pfaName_ops, legislation_ops):
   #print(dfPFA.year.unique())
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['pfaName'] == pfaName_ops]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
   dfPFA_ops_agg_ts = dfPFA_ops.groupby(['year','pfaName', 'legislation'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   dfPFA_ops_agg_ts['rateOfSearch'] = round(((
      dfPFA_ops_agg_ts['numberOfSearches'] / dfPFA_ops_agg_ts['population'])*100)*1000,0)
   
   #print(len(dfPFA_ops_agg_ts))
   return dfPFA_ops_agg_ts

# 2.1.0 Aggregate dataframe for all PFAs
#-----------------------------------------------
@pn.depends(year_ops, legislation_ops)
def create_dfPFA_ops_agg_pop(dfPFA, year_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
   dfPFA_ops_agg_pop = dfPFA_ops.groupby(['pfaName', 'legislation'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   #print(len(dfPFA_ops_agg_pop))
   return dfPFA_ops_agg_pop

# 2.1.1 Aggregate time series dataframe for all PFAs
#-----------------------------------------------
@pn.depends(pfaName_ops, year_ops, legislation_ops)
def create_dfPFA_ops_agg_pop_ts(dfPFA, year_ops, pfaName_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
   dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
   dfPFA_ops_agg_pop_ts = dfPFA_ops.groupby(['year', 'pfaName', 'legislation'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   dfPFA_ops_agg_pop_ts['rateOfSearch'] = round(((
      dfPFA_ops_agg_pop_ts['numberOfSearches'] / dfPFA_ops_agg_pop_ts['population'])*100)*1000,1)
   dfPFA_ops_agg_pop_ts.replace([np.inf, -np.inf], 0, inplace=True)
   return dfPFA_ops_agg_pop_ts


# 2.2.0 Aggregate dataframe by ethnicity for selected PFA
#---------------------------------------------------------
@pn.depends(year_ops,pfaName_ops, legislation_ops)
def create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops['pfaName'] == pfaName_ops]
   dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
   dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
   dfPFA_ops_eth_agg = dfPFA_ops.groupby(['pfaName', 'legislation', 'selfDefinedEthnicityGroup'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   return dfPFA_ops_eth_agg

# 2.1.0 Aggregate dataframe for UK by ethnicity
#-----------------------------------------------
@pn.depends(year_ops, legislation_ops)
def create_dfPFA_ops_agg_eth_uk(dfPFA, year_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0], year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
   dfPFA_ops_agg_pop = dfPFA_ops.groupby(['legislation', 'selfDefinedEthnicityGroup'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   return dfPFA_ops_agg_pop


#==============================================================================
#                             3. Function for summary text                         #                                
#==============================================================================

@pn.depends(year_ops,pfaName_ops, legislation_ops)
def summary_text(year_ops,pfaName_ops, legislation_ops):
   dfPFA_ops = create_dfPFA_ops_eth_agg(dfPFA, year_ops,pfaName_ops, legislation_ops)
   totalSearches = sum(dfPFA_ops['numberOfSearches'])
   return '##### {totalSearches} people were stopped and searched by police in {pfaName} between {startYear} and {endYear} under {legislation}.'.format(
      totalSearches=totalSearches, pfaName = pfaName_ops,
      startYear=year_ops[0],endYear=year_ops[1], legislation = legislation_ops)

#==============================================================================
#                             3. Plot functions                            #                                
#==============================================================================


# 3.1. - Number of stop and searches for selected PFA across time interval
#------------------------------------------------------------------
##16161d
@pn.depends(year_ops,pfaName_ops, legislation_ops)
def plot_num_tsline(year_ops, pfaName_ops, legislation_ops):
   
    dfPFA_tsline = create_dfPFA_ops_agg_ts(dfPFA,year_ops,pfaName_ops, legislation_ops)
    plot = {
        'chart':{
            'backgroundColor': '#1A1A1A'},#130C16 # #16161d
       "xAxis": {
           "categories": dfPFA_tsline['year']},
       "yAxis": {
           'gridLineWidth': '.25', 'title': {'enabled': False}},
       "series": [{
           'name': 'Number of stop-searches', "data": dfPFA_tsline['numberOfSearches'],"showInLegend": False,}],
       "title": {
           "text":"Number of stop-searches in "+str(pfaName_ops)+", " +str(year_ops[0])+"-" +str(year_ops[1]),
           'align':'left', 
           'style':{
               'fontSize':'18px', 'fontWeight':'300px'}},
       'plotOptions': {'series': {'color': '#E10000ED'}},
       'tooltip': {
           'pointFormat': '{series.name}: <b>{point.y:,.0f}</b>',
           'shared': True,
           'useHTML': True}
       }
    plot = ph.HighChart(object=plot, sizing_mode='stretch_width', height =270)
    return plot

# 3.2. - Stop and search incidence by ethnicity bars for selected PFA for time interval
#----------------------------------------------------------------------------------------
@pn.depends(year_ops,pfaName_ops,legislation_ops)
def plot_bar_eth_prop(year_ops, pfaName_ops, legislation_ops):
   dfPFA_ops = create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops)
   dfPFA_bar_eth_prop = dfPFA_ops
   dfPFA_bar_eth_prop['rateOfSearch'] = round(((
      dfPFA_bar_eth_prop['numberOfSearches'] / dfPFA_bar_eth_prop['population'])*100)*1000,1)
   dfPFA_bar_eth_prop.replace([np.inf, -np.inf], np.nan, inplace=True)
   dfPFA_bar_eth_prop = dfPFA_bar_eth_prop[dfPFA_bar_eth_prop["selfDefinedEthnicityGroup"].str.contains("Unknown") == False]
   plot = {
       "chart": {"type": "bar", 'backgroundColor': '#1A1A1A'},
       "xAxis": {
           "categories": dfPFA_bar_eth_prop['selfDefinedEthnicityGroup']},
       "yAxis": {
           'gridLineWidth': '.25', 'title': {'enabled': False}},
       "series": [{
           'name': 'Rate of stop and search per 1,000 people', "data": dfPFA_bar_eth_prop['rateOfSearch'],"showInLegend": False,}],
   "title": {
       "text":"Rate of stop and search per 1,000 people by ethnicity in\n" + str(pfaName_ops) +", "+str(year_ops[0])+"-"+str(year_ops[1]),
       'align':'left', 
       'style':{
           'fontSize':'18px', 'fontWeight':'300px'}},
   'plotOptions': {'series': {'color': '#E10000ED', 'borderColor': '#E10000'},
                  'dataLabels':{'enabled':True, 'y':1, 'style': {'fontWeight': 'bold', 'fontSize':'14.5px'}}
                   },
   'tooltip': {
       'pointFormat':'{series.name}: <b>{point.y:,.0f}</b>',
       'shared': True,
       'useHTML': True}
   }
   plot = ph.HighChart(object=plot, height =270, width = 460)
   return plot


# 3.4. - Number stop and search for selected PFA versus other PFA across time interval
#-----------------------------------------------------------------------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops)
def plot_tsscatter(year_ops, pfaName_ops, legislation_ops):
   dfPFA_tsscatter = create_dfPFA_ops_agg_pop_ts(dfPFA, year_ops, pfaName_ops, legislation_ops)
   dfPFA_tsscatter = dfPFA_tsscatter.drop(columns=['numberOfSearches'])
   dfPFA_tsscatter_wide = dfPFA_tsscatter.pivot(index='year', columns='pfaName', values='rateOfSearch').reset_index()
   dfPFA_tsscatter_main = dfPFA_tsscatter_wide[['year', pfaName_ops]]
   dfPFA_tsscatter_other = dfPFA_tsscatter_wide.drop(columns=[pfaName_ops])
   listPFAseries = []
   rnd.seed(115520)
   ###add line that varies jitter by number of years
   for col in dfPFA_tsscatter_other.loc[:, dfPFA_tsscatter_other.columns != 'year']:
      xNoise = rnd.uniform(0, 0.4)
      yNoise = rnd.uniform(0, 0.2)
      listPFAseries.append({'name': col, 'color': '#d3d3d399', 'borderColor':'#d3d3d3', "data": dfPFA_tsscatter_other[col], 'marker': {'enabled': True, 'symbol': "circle", 'radius': 2.5}, 'jitter':{'x':xNoise, 'y':yNoise}, "showInLegend": False},)
   listPFAseries.append({'name': pfaName_ops, 'color': '#E10000ED', 'borderColor':'#E10000', "data": dfPFA_tsscatter_main[pfaName_ops], 'marker': {'enabled': True, 'symbol': "circle", 'radius': 10},"showInLegend": False},)
   if pfaName_ops != 'Metropolitan Police': yMax = dfPFA_tsscatter[dfPFA_tsscatter['pfaName'] != 'Metropolitan Police']['rateOfSearch'].max() 
   else: yMax = dfPFA_tsscatter['rateOfSearch'].max() 
   plot = {
       "chart": {"type":"scatter", 'backgroundColor':'#1A1A1A', 'inverted':True},
       "xAxis": {'categories': dfPFA_tsscatter_wide['year']},
       "yAxis": {
           'gridLineWidth':'.25', 'title': {'enabled':False}, 'max':yMax},
       "series": listPFAseries,
   "title": {
       "text":"Rate of stop and search per 1,000 people in " + str(pfaName_ops) +" compared to other PFAs, "+str(year_ops[0])+"-"+str(year_ops[1]),
       'align':'left', 
       'style':{
           'fontSize':'18px', 'fontWeight':'300px'}},
   'plotOptions':{'series':{'color': '#E1000066'}},
   'tooltip': {
       'pointFormat': '{series.name}: <b>{point.y:,.0f}</b>',
       'shared': True,
       'useHTML': True}
   }
   plot = ph.HighChart(object=plot, sizing_mode="fixed", height=600, width=460)
   return plot


# 3.5.
#------------------------
@pn.depends(year_ops, legislation_ops)
def plot_bar_odds_ratio_UK(year_ops, legislation_ops):
   df = create_dfPFA_ops_agg_eth_uk(dfPFA, year_ops, legislation_ops)
   df['rateOfSearches'] = ((df['numberOfSearches'] / df['population'])*100)
   ethnicity_index = df['selfDefinedEthnicityGroup'].values
   df.set_index(ethnicity_index, inplace = True)
   df = df.loc[['White', 'Asian', 'Black', 'Mixed', 'Other Ethnic Group'], :]
   df['ratios'] = [round(i/df['rateOfSearches']['White'], 1) for i in df['rateOfSearches']]
   df.replace([np.inf, -np.inf], np.nan, inplace=True)
   #df['index'] = 1
   #df = df.pivot(index='index', columns=['selfDefinedEthnicityGroup'], values='ratios')
   plot = {
     'chart': {"type": "bar", 'backgroundColor': '#1A1A1A'},
     'xAxis': {'categories': df['selfDefinedEthnicityGroup']},
     'yAxis': {'gridLineWidth': '.25', 'title': {'enabled': False}},
     'series': [
        {'name': 'Odds of stop and search relative to people of white ethnicity', "data": df['ratios'],"showInLegend": False, 'colorByPoint':True},
      ],
      'title': {
      'text':"Ethnic disparities in stop and search (odds ratios) in England and Wales, " +str(year_ops[0])+"-"+str(year_ops[1]),
      'align':'left', 
      'style':{
         'fontSize':'18px', 'fontWeight':'300px'}},
      'plotOptions': {'series': {'colors': ['#d3d3d3D9', '#E10000ED','#E10000ED', '#E10000ED','#E10000ED'] ,
                                 'borderColor': ['#d3d3d3', '#E10000','#E10000', '#E10000','#E10000'],
                      'dataLabels':{'enabled':True, 'y':1, 'style': {'fontWeight': 'bold', 'fontSize':'14.5px'}}}},
      'tooltip': {
      'pointFormat':'{series.name}: <b>{point.y:,.1f}</b>',
      'shared': True,
      'useHTML': True}
   }
   plot = ph.HighChart(object=plot, sizing_mode='fixed', height=270, width=570)
   return plot


# 3.5.
#------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops)
def plot_bar_odds_ratio_PFA(year_ops, pfaName_ops, legislation_ops):
   df = create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops)
   df['rateOfSearches'] = ((df['numberOfSearches'] / df['population'])*100)
   ethnicity_index = df['selfDefinedEthnicityGroup'].values
   df.set_index(ethnicity_index, inplace = True)
   df['ratios'] = [round(i/df['rateOfSearches']['White'], 1) for i in df['rateOfSearches']]
   df.replace([np.inf, -np.inf], np.nan, inplace=True)
   plot = {
     'chart': {"type": "bar", 'backgroundColor': '#1A1A1A'},
     'xAxis': {'categories': df['selfDefinedEthnicityGroup']},
     'yAxis': {'gridLineWidth': '.25', 'title': {'enabled': False}},
     'series': [
        {'name': 'Odds of stop and search relative to people of white ethnicity', "data": df['ratios'],"showInLegend": False, 'colorByPoint':True},
      ],
      'title': {
      'text':"Ethnic disparities in stop and search (odds ratios) in "+str(pfaName_ops) +", "+str(year_ops[0])+"-"+str(year_ops[1]),
      'align':'left', 
      'style':{
         'fontSize':'18px', 'fontWeight':'300px'}},
      'plotOptions': {'series': {'colors': ['#d3d3d3D9', '#E10000ED','#E10000ED', '#E10000ED','#E10000ED'] ,
                                 'borderColor': ['#d3d3d3', '#E10000','#E10000', '#E10000','#E10000'],
                      'dataLabels':{'enabled':True, 'y':1, 'style': {'fontWeight': 'bold', 'fontSize':'14.5px'}}}},
      'tooltip': {
      'pointFormat':'{series.name}: <b>{point.y:,.1f}</b>',
      'shared': True,
      'useHTML': True}
   }
   plot = ph.HighChart(object=plot, sizing_mode='fixed', height =270, width = 570)
   return plot





# 3.6. - Police Force Area map
#-----------------------------------------------------------------------------------------
@pn.depends(year_ops,pfaName_ops, legislation_ops)
def map_pfa(year_ops, pfaName_ops, legislation_ops):
   
    # Load options dataframe and add geometries
   df = create_dfPFA_ops_agg_pop(dfPFA, year_ops, legislation_ops)
   dfBounds = pd.merge(boundsPFA, df[['pfaName','numberOfSearches']],
                       left_on='name', right_on='pfaName', how='left')
   # Mapping for map plot options
   mapOps = dfBounds.loc[dfBounds['pfaName'] != 'Metropolitan Police', ['pfaName', 'numberOfSearches']]
   tempMet = dfBounds.loc[dfBounds['pfaName'] == 'Metropolitan Police', ['pfaName', 'numberOfSearches']]
   mapOps['elevation'] = (mapOps['numberOfSearches'] - np.min(mapOps['numberOfSearches'])) / (np.max(mapOps['numberOfSearches']) - np.min(mapOps['numberOfSearches']))
   mapOps = pd.merge(mapOps, tempMet, on=['pfaName','numberOfSearches'], how='outer')
   mapOps['elevation'] = np.where(mapOps['pfaName'] == 'Metropolitan Police', mapOps.sort_values("elevation", ascending=False)['elevation'].iloc[0]*1.95, mapOps['elevation'])
   mapOps['decile'] = pd.qcut(mapOps['numberOfSearches'], 10, labels=False)
   colorsR = [i*.9 for i in [255,254,253,253,252,243,225,208,190,173]]
   colorsG = [i*.9 for i in [247,228,209,190,171,144,108,72,36,0]]
   colorsB = [i*.9 for i in [236,207,179,151,123,96, 72,48,24,0]]
   mapOps['fillR'] = 0
   mapOps['fillG'] = 0
   mapOps['fillB'] = 0
   for i in range(len(mapOps)):
      d = mapOps['decile'].iloc[i]
      mapOps['fillR'].iloc[i] = colorsR[d]
      mapOps['fillG'].iloc[i] = colorsG[d]
      mapOps['fillB'].iloc[i] = colorsB[d]
   # Add plot option mapping to main dataframe
   dfBoundsOps = pd.merge(dfBounds, mapOps[['pfaName', 'elevation', 'decile', 'fillR', 'fillG', 'fillB']], on='pfaName', how='left')
   dfBoundsOps['numberOfSearches'] = dfBoundsOps['numberOfSearches'].apply(lambda d: f'{round(d, 2):,}')
   dfBoundsOps['lineR'] = np.where(dfBoundsOps['pfaName'] == pfaName_ops, 0, mapOps['fillR']) 
   dfBoundsOps['lineG'] = np.where(dfBoundsOps['pfaName'] == pfaName_ops, 0, mapOps['fillG']) 
   dfBoundsOps['lineB'] = np.where(dfBoundsOps['pfaName'] == pfaName_ops, 0, mapOps['fillB']) 
   
   
   dfBoundsOps_pfa = dfBoundsOps[dfBoundsOps['pfaName'] == pfaName_ops]

   dfBoundsOps_pfa['lng'] = dfBoundsOps_pfa.centroid.x
   dfBoundsOps_pfa['lat'] = dfBoundsOps_pfa.centroid.y
   pfa_lng = dfBoundsOps_pfa['lng'].iloc[0]
   pfa_lat = dfBoundsOps_pfa['lat'].iloc[0]
   pfa_ele = dfBoundsOps_pfa['elevation'].iloc[0]+1.5
   d = {'lng': pfa_lng, 'lat': pfa_lat, "price_per_unit_area": pfa_ele}
   dff = pd.DataFrame(data=d, index=[0])
   print(dff)
   column_layer = pdk.Layer(
       "ColumnLayer",
       data=dff,
       get_position=["lng", "lat"],
       get_elevation="price_per_unit_area",
       elevation_scale=50000,
       radius=7000,
       #get_fill_color=[211, 211, 211, 250],
      get_fill_color=[253, 231, 37, 250],
       #get_fill_color=[0, 173, 236, 250],
       #get_fill_color=[87, 236,0, 250], 
       #get_fill_color=[253, 231, 37, 250],
       #get_fill_color=[0, 173,0, 250],
       pickable=False,
       auto_highlight=False,
   )


   polygon_3d = pdk.Layer(
      "GeoJsonLayer",
      dfBoundsOps,
      wireframe=True,
      get_fill_color="[fillR, fillG, fillB]",
      #get_line_color="[fillR, fillG, fillB]",
      get_line_color=[30,30,30],
      #highlight_color=[127, 0, 255, 100],
      auto_highlight=True,
      extruded=True,
      get_elevation='elevation',
      elevation_scale=50000,
      pickable=True
    )
   view_state = pdk.ViewState(
      longitude=-1.415,
      latitude=52.2323,
      zoom=5.3,
      min_zoom=5.3,
      max_zoom=15,
      pitch=40.5,
      bearing=-25.36
   )
   tooltip = {
      "html": "Police Force Area: <b>{pfaName}</b><br>Number of stop-searches: <b>{numberOfSearches}</b>",
      "style": {
         "backgroundColor": "rgb(26, 26, 26)",
         "color": "white",
         "font-family": "Helvetica",
         "font-size": "14px",
         "max-width": "220px"
      }
   } 
   # Combine map elements and render as Panel pane
   deckMap = pdk.Deck(layers=[polygon_3d, column_layer], initial_view_state=view_state, tooltip=tooltip)
   map_pane = pn.pane.DeckGL(deckMap, height=585, width=690)
   return map_pane

@pn.depends(year_ops,pfaName_ops, legislation_ops)
def map_pfa_title(year_ops,pfaName_ops, legislation_ops):
    title_html =pn.pane.Markdown('Number of stop-searches in '+str(pfaName_ops) +' compared to other PFAs, '+str(year_ops[0])+"-"+str(year_ops[1]), 
                                 style={"font-family": "Lucida Sans Unicode", "color": "white", 'font-size':'18px', 'font-weight':'300px', 'background-color': '#2C353C','border-radius': '0px', "padding-left":"15px"},margin=(0, 0, -9, -9))
    return title_html
#181818

###################################################################################

###############################################################################
logo = pn.panel(r"C:\Users\Matt\Git\StopWatch\sourceData\stopwatch_logo.png", width=250, align='start')
import base64
def image_to_data_url(filename):
    ext = filename.split('.')[-1]
    prefix = f'data:image/{ext};base64,'
    with open(filename, 'rb') as f:
        img = f.read()
    return prefix + base64.b64encode(img).decode('utf-8')
logo2 = image_to_data_url(r"C:\Users\Matt\Git\StopWatch\sourceData\stopwatch_logo.png")
#logo2 = image_to_data_url('stopwatch_logo.png')

#one = pn.widgets.Button(name='Overview', width=50, button_type='primary', height = 35)
#two = pn.widgets.Button(name='Ethnic Disparities', width=50, button_type='primary', height = 35)
#toggle_group = pn.widgets.ToggleGroup(name='ToggleGroup', options=['Overview', 'Ethnic Disparities'], 
                                      #behavior="radio", height = 35)
                                      
                                      
html_pane = pn.pane.HTML("""
<h1>Key Statistics</h1>

<code>
x = 5;<br>
y = 6;<br>
z = x + y;
</code>

<br>
<br>

<table>
  <tr>
    <th>Firstname</th>
    <th>Lastname</th> 
    <th>Age</th>
  </tr>
  <tr>
    <td>Jill</td>
    <td>Smith</td> 
    <td>50</td>
  </tr>
  <tr>
    <td>Eve</td>
    <td>Jackson</td> 
    <td>94</td>
  </tr>
</table>
""", style={'background-color': '#202020', 'border': '#202020',
            'border-radius': '5px', 'padding': '20px'})

                         ##181818
html_pane

html_pane.style = dict(html_pane.style, border='2px solid #202020')


# same as title

#, favicon = logo2
from panel.template import DarkTheme
template = pn.template.FastGridTemplate(theme =  "dark",
    site="", title="Interactive Stop and Search Tracker",
    sidebar=[logo, year_ops, pfaName_ops, legislation_ops, summary_text, html_pane],
    sidebar_width = 380, header_background = '#130C16', header_accent_base_color = '#130C16',
    header_neutral_color = '#130C16', accent_base_color = '#130C16', corner_radius = 6, shadow = False, 
    prevent_collision = True, theme_toggle = False#, cols = {'lg': 18, 'md': 12, 'sm': 8, 'xs': 6, 'xxs': 4}
)



#neutral_color = ,
#  background_color = '#130C16'
template.main[:2, :7] = plot_num_tsline
template.main[:2, 7:12]=plot_bar_eth_prop
template.main[2:6, :7]=pn.Column(map_pfa_title,map_pfa)
template.main[2:6, 7:12]=plot_tsscatter
template.main[6:8, :6]=plot_bar_odds_ratio_UK
template.main[6:8, 6:12]=plot_bar_odds_ratio_PFA
template.show()
#pn.serve(template)


#Number of stop-searches 
#Ethnic disparities in stop and search
# map stop search title
#HTML info text
# look into 2021 bug
# consider table options and data download options
#ipconfig/flushdns