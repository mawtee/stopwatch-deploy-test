# -*- coding: utf-8 -*-
"""
Created on Sat Mar 18 13:00:49 2023

@author: MatthewTibbles
"""

from panel.template import DarkTheme
import base64
import numpy as np
import random as rnd
import pandas as pd
import geopandas as gpd
import panel as pn
import panel_highcharts as ph
import pydeck as pdk
pn.extension("highchart", template="fast", sizing_mode="stretch_width")
pn.extension('deckgl')
ph.config.theme(name="high-contrast-dark")
rnd.seed(115520)


#import bokeh.io
#from bokeh.models import Title
#from bokeh.models import LabelSet
#from bokeh.models import ColumnDataSource
# hv.extension('bokeh')
# hv.extension('plotly')


# year = pn.widgets.IntRangeSlider(name=’Select year’, width=250, start=2011, end=201, value=(2011, 2021), value_throttled=(1985, 2016))


# Loading Data
#dfPFA = pd.read_csv('dfPFA_clean.csv')
dfPFA = pd.read_csv("dfPFA_clean.csv", low_memory=False)
boundsPFA = gpd.read_file("pfa_merged_bounds_sm2.geojson")

# Bar chart
# @pn.depends(year.param.value_throttled)
# def plot_bar(year):
#   years_df = df[df.Began.dt.year.between(year[0], year[1])]
#   bar_table = years_df[“MainCause”]
#     .value_counts()
#     .reset_index()
#    .rename(columns={“index”:’Cause’, “MainCause”:”Total”})
#    return bar_table[:10].sort_values(“Total”)
#    .hvplot.barh(“Cause”, “Total”,
#      invert=False, legend=’bottom_right’, height=600)


# CSS classes
widget_box_css = '''
.bk.widget-box {
  background: #1a1a1a;
  border-radius:7px;
  border-left: 7px solid #d9d9d9 !important;
  padding-left: 10px; 
  }
  
'''
radio_button_css = """
.bk.bk-btn.bk-btn-default {
  font-size: 103%;
}
"""


pn.extension(raw_css=[widget_box_css])
pn.extension(raw_css=[radio_button_css])


def make_ordinal(n):
    '''
    Convert an integer into its ordinal representation::

        make_ordinal(0)   => '0th'
        make_ordinal(3)   => '3rd'
        make_ordinal(122) => '122nd'
        make_ordinal(213) => '213th'
    '''
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix
# ================================================================================================
#                                         1. Sidebar widgets                                    #
# ================================================================================================

# 1.0. Year range slider
# --------------------------
startYear = dfPFA.year.min().astype('int').item()
endYear = dfPFA.year.max().astype('int').item()
year_ops = pn.widgets.IntRangeSlider(
    name='What year(s) would like to visualise?',
    start=startYear, end=endYear,
    value=(startYear, endYear), value_throttled=(startYear, endYear),
    step=1, bar_color='#E10000', width=365)

# 1.1. PFA area drop down list
# ---------------------------------
pfaName_list = dfPFA.pfaName.unique().tolist()
pfaName_ops = pn.widgets.Select(name='What Police Force Area (PFA) would you like to visualise?',
                                options=pfaName_list, width=365, margin=(6, 0, 6, 10))

# 1.2. Legislation drop down list
# -----------------------------------
legislation_list = dfPFA.legislation.unique().tolist()
legislation_ops = pn.widgets.Select(
    name='Which legislation would like to visualise?', options=legislation_list, width=365, margin=(6, 0, 6, 10))


add_params_ops = pn.widgets.Checkbox(
    name='View additional parameters', margin=(6, 0, 6, 10))
population_ops = pn.widgets.Select(name='Change population denominator', options=[
                                   'Unadjusted (carried-forward census values)', 'Adjusted (interpolated census estimates)'], width=375, margin=(6, 0, 6, 10), visible=False)
colorpicker = pn.widgets.ColorPicker(
    name='Change map marker color', value='#d3d3d3', visible=False)

# pn.Row(
#  pn.Column(pn.widgets.ColorPicker(value='#d3d3d3')c width=50, height=5, margin=(0,0,0,0)),
#  pn.Column(pn.pane.HTML("""Change map marker colour""")))


# , margin=(0,0,50,10)


# ==================================================================================================
#                                    2. Options based dataframes                                  #
# ==================================================================================================

# 2.0.0 Aggregate dataframe for selected PFA
# -----------------------------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def create_dfPFA_ops_agg(dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol' 
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['pfaName'] == pfaName_ops]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_agg = dfPFA_ops.groupby(['pfaName', 'legislation'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    dfPFA_ops_agg['rateOfSearch'] = round(((
        dfPFA_ops_agg['numberOfSearches'] / dfPFA_ops_agg[pop])*100)*1000, 0)
    return dfPFA_ops_agg

# 2.0.1 Aggregate time-series dataframe for selected PFA
# -----------------------------------------------


@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def create_dfPFA_ops_agg_ts(dfPFA, year_ops, pfaName_ops, legislation_ops,population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol' 
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['pfaName'] == pfaName_ops]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_agg_ts = dfPFA_ops.groupby(['year', 'pfaName', 'legislation'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    dfPFA_ops_agg_ts['rateOfSearch'] = round(((
        dfPFA_ops_agg_ts['numberOfSearches'] / dfPFA_ops_agg_ts[pop])*100)*1000, 0)

    # print(len(dfPFA_ops_agg_ts))
    return dfPFA_ops_agg_ts

# 2.1.0 Aggregate dataframe for all PFAs
# -----------------------------------------------

@pn.depends(year_ops, legislation_ops, population_ops)
def create_dfPFA_ops_agg_pop(dfPFA, year_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_agg_pop = dfPFA_ops.groupby(['pfaName', 'legislation'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    # print(len(dfPFA_ops_agg_pop))
    return dfPFA_ops_agg_pop

# 2.1.1 Aggregate time series dataframe for all PFAs
# -----------------------------------------------


@pn.depends(pfaName_ops, year_ops, legislation_ops, population_ops)
def create_dfPFA_ops_agg_pop_ts(dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_agg_pop_ts = dfPFA_ops.groupby(['year', 'pfaName', 'legislation'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    dfPFA_ops_agg_pop_ts['rateOfSearch'] = round(((
        dfPFA_ops_agg_pop_ts['numberOfSearches'] / dfPFA_ops_agg_pop_ts[pop])*100)*1000, 1)
    dfPFA_ops_agg_pop_ts.replace([np.inf, -np.inf], 0, inplace=True)
    return dfPFA_ops_agg_pop_ts


# 2.2.0 Aggregate dataframe by ethnicity for selected PFA
# ---------------------------------------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['pfaName'] == pfaName_ops]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_eth_agg = dfPFA_ops.groupby(['pfaName', 'legislation', 'selfDefinedEthnicityGroup'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    return dfPFA_ops_eth_agg

# 2.2.0 Aggregate dataframe by ethnicity for all PFAs
# ---------------------------------------------------------
@pn.depends(year_ops, legislation_ops, population_ops)
def create_dfPFA_ops_eth_agg_pop(dfPFA, year_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_eth_agg = dfPFA_ops.groupby(['pfaName', 'legislation', 'selfDefinedEthnicityGroup'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    return dfPFA_ops_eth_agg

# 2.1.0 Aggregate dataframe for UK by ethnicity
# -----------------------------------------------


@pn.depends(year_ops, legislation_ops, population_ops)
def create_dfPFA_ops_agg_eth_uk(dfPFA, year_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    dfPFA_ops = dfPFA[dfPFA['year'].between(
        year_ops[0], year_ops[1], inclusive='both')]
    dfPFA_ops = dfPFA_ops[dfPFA_ops['legislation'] == legislation_ops]
    dfPFA_ops['year'] = dfPFA_ops['year'].astype('str')
    dfPFA_ops_agg_pop = dfPFA_ops.groupby(['legislation', 'selfDefinedEthnicityGroup'], as_index=False)[[
        'numberOfSearches', pop]].sum()
    return dfPFA_ops_agg_pop


# ==============================================================================
#                             3. Function for summary text                         #
# ==============================================================================
 
#@pn.depends(year_ops, pfaName_ops, legislation_ops)
#class key_stats_html_update(dfPFA):
#    dfPFA_ops = create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops)
#    #@pn.depends(year_ops, pfaName_ops, legislation_ops)
#    def load(self):
#        dfPFA_ops = create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops)
#        totalSearches = sum(dfPFA_ops['numberOfSearches'])
#        @pn.depends("totalSearches")
#        def updatee(self):
#          update = pn.pane.Markdown(
#           f"""
#           ###Key statistics
#           {self.totalSearches} people were stopped and searched by police in
#           """) 
#          return update

#https://discourse.holoviz.org/t/simple-text-with-dynamic-part/1467/2
#@pn.depends(year_ops, pfaName_ops, legislation_ops)
#class UpdateText(dfPFA):
#    dfPFA_ops = create_dfPFA_ops_eth_agg(dfPFA, year_ops, pfaName_ops, legislation_ops)
#    totalSearches = sum(dfPFA_ops['numberOfSearches'])
    #pfaName = pfaName_ops
    #startYear = year_ops[0]
    #endYear = year_ops[1]
    #legislation = legislation_ops

#    @pn.depends(totalSearches)
#    def summary_vals(self):
#        update = pn.pane.Markdown(
#            f"""
#            ###Key statistics
#            {self.totalSearches} people were stopped and searched by police in
 #          """) 
#        return update


#key_stats_html = key_stats_html_update()



#@pn.depends(year_ops, pfaName_ops, legislation_ops)
#def summary_text(year_ops, pfaName_ops, legislation_ops):
#    dfPFA_ops = create_dfPFA_ops_eth_agg(
#        dfPFA, year_ops, pfaName_ops, legislation_ops)
#    totalSearches = sum(dfPFA_ops['numberOfSearches'])
#    return '##### {totalSearches} ##people were stopped and searched by police in {pfaName} between {startYear} and {endYear} under {legislation}.'.format(
 #       totalSearches=totalSearches, pfaName=pfaName_ops,
#        startYear=year_ops[0], endYear=year_ops[1], legislation=legislation_ops)



@pn.depends(add=add_params_ops, watch=True)
def vis_add_param_ops(add):
    population_ops.visible = add == True
    colorpicker.visible = add == True






footer_ops = pn.widgets.RadioButtonGroup(options=['Area fact-sheet', 'Reference notes'],
                                         button_type='default', height=35, width=375, margin=(6, 0, 6, 10), css_classes=['radio'])



@pn.depends(year_ops, pfaName_ops, legislation_ops, footer_ops, population_ops)
def key_stats_html(year_ops, pfaName_ops, legislation_ops, footer_ops, population_ops):
  
  if population_ops == 'Unadjusted (carried-forward census values)':
    pop = 'population'
  else:
   pop = 'populationIpol'
    
  dfPFA_ops_agg = create_dfPFA_ops_agg(dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops)
  dfPFA_ops_agg_pop_ts = create_dfPFA_ops_agg_pop_ts(dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops)
  
  # Overview stats
  totalSearches_pfa = sum(dfPFA_ops_agg['numberOfSearches'])
  searchRate_pfa = int(dfPFA_ops_agg.loc[dfPFA_ops_agg['pfaName'] == pfaName_ops, 'rateOfSearch']) 
  meanSearches_all = dfPFA_ops_agg_pop_ts['numberOfSearches'].mean().astype(int)
  meanSearchRate_all = dfPFA_ops_agg_pop_ts['rateOfSearch'].mean().astype(int)
  dfPFA_ops_agg_pop_ts['totalSearches'] = dfPFA_ops_agg_pop_ts.groupby(['pfaName'], as_index=False)[[
      'numberOfSearches']].transform('sum')
  dfPFA_ops_agg_pop_ts = dfPFA_ops_agg_pop_ts.drop_duplicates(subset = "pfaName")
  dfPFA_ops_agg_pop_ts['numRank'] = dfPFA_ops_agg_pop_ts['totalSearches'].rank(ascending=False).astype(int)
  totalSearchesRank_pfa = make_ordinal(int(dfPFA_ops_agg_pop_ts.loc[dfPFA_ops_agg_pop_ts['pfaName'] == pfaName_ops, 'numRank']))
  dfPFA_ops_agg_pop_ts['rateRank'] = dfPFA_ops_agg_pop_ts['rateOfSearch'].rank(ascending=False).astype(int)
  searchRateRank_pfa = make_ordinal(int(dfPFA_ops_agg_pop_ts.loc[dfPFA_ops_agg_pop_ts['pfaName'] == pfaName_ops, 'rateRank']))
  
  # Ethnic Disparities
  dfPFA_ops_eth_agg = create_dfPFA_ops_eth_agg(
      dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops)
  dfPFA_ops_eth_agg['rateOfSearches'] = ((dfPFA_ops_eth_agg['numberOfSearches'] / dfPFA_ops_eth_agg[pop])*100)
  ethnicity_index = dfPFA_ops_eth_agg['selfDefinedEthnicityGroup'].values
  dfPFA_ops_eth_agg.set_index(ethnicity_index, inplace=True)
  dfPFA_ops_eth_agg = dfPFA_ops_eth_agg.loc[['White', 'Asian', 'Black', 'Mixed', 'Other Ethnic Group'], :]
  dfPFA_ops_eth_agg['ratios'] = [round(i/dfPFA_ops_eth_agg['rateOfSearches']['White'], 2)for i in dfPFA_ops_eth_agg['rateOfSearches']]
  dfPFA_ops_eth_agg.replace([np.inf, -np.inf], np.nan, inplace=True)
  
  asianOdds_pfa = dfPFA_ops_eth_agg['ratios'].iloc[1] 
  blackOdds_pfa = dfPFA_ops_eth_agg['ratios'].iloc[2] 
  mixedOdds_pfa = dfPFA_ops_eth_agg['ratios'].iloc[3]
  otherOdds_pfa = dfPFA_ops_eth_agg['ratios'].iloc[4]
  
  
  dfPFA_ops_eth_agg_pop=create_dfPFA_ops_eth_agg_pop(dfPFA, year_ops, legislation_ops, population_ops)
  dfPFA_ops_eth_agg_pop['rateOfSearches'] = ((dfPFA_ops_eth_agg_pop['numberOfSearches'] / dfPFA_ops_eth_agg_pop[pop])*100)
  dfPFA_ops_eth_agg_pop['White'] = np.where(dfPFA_ops_eth_agg_pop['selfDefinedEthnicityGroup'] == 'White', dfPFA_ops_eth_agg_pop['rateOfSearches'], np.nan)
  dfPFA_ops_eth_agg_pop['White'] = dfPFA_ops_eth_agg_pop.groupby('pfaName').White.transform('first')
  dfPFA_ops_eth_agg_pop['ratios'] = round(dfPFA_ops_eth_agg_pop['rateOfSearches']/dfPFA_ops_eth_agg_pop['White'],2)
  dfPFA_ops_eth_agg_pop.replace([np.inf, -np.inf], np.nan, inplace=True)
  dfPFA_ops_eth_agg_pop['ratiosMean'] = dfPFA_ops_eth_agg_pop.groupby('selfDefinedEthnicityGroup', as_index=False)['ratios'].transform('mean').round(2)
  dfPFA_ops_eth_agg_pop.replace([np.nan], 0, inplace=True) # can drop this line when Devon is sorted
  
  asianOddsMean_all = dfPFA_ops_eth_agg_pop['ratiosMean'].iloc[0]
  blackOddsMean_all = dfPFA_ops_eth_agg_pop['ratiosMean'].iloc[1]
  mixedOddsMean_all = dfPFA_ops_eth_agg_pop['ratiosMean'].iloc[2]
  otherOddsMean_all = dfPFA_ops_eth_agg_pop['ratiosMean'].iloc[3]

  dfPFA_ops_eth_agg_pop_asian = dfPFA_ops_eth_agg_pop[dfPFA_ops_eth_agg_pop['selfDefinedEthnicityGroup'] == 'Asian']
  dfPFA_ops_eth_agg_pop_asian['oddsRank'] = dfPFA_ops_eth_agg_pop_asian['ratios'].rank(ascending=False).astype(int)
  oddsRankAsian_pfa = make_ordinal(int(dfPFA_ops_eth_agg_pop_asian.loc[dfPFA_ops_eth_agg_pop_asian['pfaName'] == pfaName_ops, 'oddsRank']))
  dfPFA_ops_eth_agg_pop_black = dfPFA_ops_eth_agg_pop[dfPFA_ops_eth_agg_pop['selfDefinedEthnicityGroup'] == 'Black']
  dfPFA_ops_eth_agg_pop_black['oddsRank'] = dfPFA_ops_eth_agg_pop_black['ratios'].rank(ascending=False).astype(int)
  oddsRankBlack_pfa = make_ordinal(int(dfPFA_ops_eth_agg_pop_black.loc[dfPFA_ops_eth_agg_pop_black['pfaName'] == pfaName_ops, 'oddsRank']))
  dfPFA_ops_eth_agg_pop_mixed = dfPFA_ops_eth_agg_pop[dfPFA_ops_eth_agg_pop['selfDefinedEthnicityGroup'] == 'Mixed']
  dfPFA_ops_eth_agg_pop_mixed['oddsRank'] = dfPFA_ops_eth_agg_pop_mixed['ratios'].rank(ascending=False).astype(int)
  oddsRankMixed_pfa = make_ordinal(int(dfPFA_ops_eth_agg_pop_mixed.loc[dfPFA_ops_eth_agg_pop_mixed['pfaName'] == pfaName_ops, 'oddsRank']))
  dfPFA_ops_eth_agg_pop_other = dfPFA_ops_eth_agg_pop[dfPFA_ops_eth_agg_pop['selfDefinedEthnicityGroup'] == 'Other Ethnic Group']
  dfPFA_ops_eth_agg_pop_other['oddsRank'] = dfPFA_ops_eth_agg_pop_other['ratios'].rank(ascending=False).astype(int)
  oddsRankOther_pfa = make_ordinal(int(dfPFA_ops_eth_agg_pop_other.loc[dfPFA_ops_eth_agg_pop_other['pfaName'] == pfaName_ops, 'oddsRank']))

  # if London remove string Police
  key_stats = pn.pane.HTML(
    f"""
    <h2>Overview</h2>
    <hr style="max-width:370px;margin: 0px; margin-bottom:10px;margin-top:-10px;">
    <br><b>Number -</b> {'{:,}'.format(totalSearches_pfa)} stop-searches were recorded by {pfaName_ops} police between {year_ops[0]} and {year_ops[1]}:
    <ul>
      <li>The average number of searches recorded across England and Wales during this period was  {'{:,}'.format(meanSearches_all)}, ranking {pfaName_ops} police {totalSearchesRank_pfa} out 42 PFAs.</li>
    </ul>
    <br><b>Rate -</b> {searchRate_pfa} stop-searches were recorded for every 1,000 people living in {pfaName_ops} between {year_ops[0]} and {year_ops[1]}:
     <ul>
       <li>The average stop and search rate across England and Wales during this period was {'{:,}'.format(meanSearchRate_all)} per 1,000 people, ranking {pfaName_ops} police {searchRateRank_pfa} out of 42 PFAs.</li>
     </ul>  
    <h2>Ethnic disparities</h2>
    <hr style="max-width:370px;margin: 0px;margin-bottom:10px;margin-top:-10px;">
    <br><b>Asian -</b> Asian people were {asianOdds_pfa} times as likely as White people to be stopped by {pfaName_ops} police between {year_ops[0]} and {year_ops[1]}:
    <ul>
      <li> The average stop-search odds for Asian people across England and Wales was {asianOddsMean_all}, ranking {pfaName_ops} police {oddsRankAsian_pfa} out of 42 PFAs.</li>
    </ul>
    <br><b>Black -</b> Black people were {blackOdds_pfa} times as likely as White people to be stopped by {pfaName_ops} police between {year_ops[0]} and {year_ops[1]}:
    <ul>
      <li> The average stop-search odds for Black people across England and Wales was {blackOddsMean_all}, ranking {pfaName_ops} police {oddsRankBlack_pfa} out of 42 PFAs.</li>
    </ul>
    <br><b>Mixed -</b> People of Mixed ethnicity were {mixedOdds_pfa} times as likely as White people to be stopped by {pfaName_ops} police between {year_ops[0]} and {year_ops[1]}:
    <ul>
      <li> The average stop-search odds for people of Mixed ethnicity across England and Wales was {mixedOddsMean_all}, ranking {pfaName_ops} police {oddsRankMixed_pfa} out of 42 PFAs.</li>
    </ul>
    <br><b>Other Ethnic Groups -</b> People from Other Ethnic Groups were {otherOdds_pfa} times as likely as White people to be stopped by {pfaName_ops} police between {year_ops[0]} and {year_ops[1]}:
    <ul>
      <li> The average stop-search odds for people from Other Ethnic Groups across England and Wales was {otherOddsMean_all}, ranking {pfaName_ops} police {oddsRankOther_pfa} out of 42 PFAs.</li>
    </ul>
    """
    , style={'padding-top': '-270px', 'margin-top': '-20px'})
  if footer_ops =='Key statistics':
      key_stats.visible=True
  if footer_ops =='Reference notes':
      key_stats.visible=False
  return key_stats


@pn.depends(footer_ops, watch=True)
def ref_notes_html(footer_ops):
  ref_notes = pn.pane.HTML("<h1>Reference notes</h1>", style={
                              'padding-top': '-250px', 'margin-top': '-20px'}, visible=False)
  if footer_ops =='Reference notes':
      ref_notes.visible=True
  if footer_ops =='Key statistics':
      ref_notes.visible=False
  return ref_notes




main_ops_pane = pn.Row(pn.Column(
    pn.WidgetBox(year_ops, pfaName_ops, legislation_ops, add_params_ops, colorpicker, population_ops)), css_classes=['widget-box'])
footer_pane = pn.Column(pn.Row(footer_ops), pn.Row(
    pn.WidgetBox(key_stats_html, ref_notes_html)), css_classes=['widget-box'])


# ==============================================================================
#                             3. Plot functions                            #
# ==============================================================================


# 3.1. - Number of stop and searches for selected PFA across time interval
# ------------------------------------------------------------------
# 16161d
@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def plot_num_tsline(year_ops, pfaName_ops, legislation_ops, population_ops):

    dfPFA_tsline = create_dfPFA_ops_agg_ts(
        dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops)
    plot = {
        'chart': {
            'backgroundColor': '#1A1A1A'},  # 130C16 # #16161d
        "xAxis": {
            "categories": dfPFA_tsline['year']},
        "yAxis": {
            'gridLineWidth': '.25', 'title': {'enabled': False}},
        "series": [{
            'name': 'Number of stop-searches', "data": dfPFA_tsline['numberOfSearches'], "showInLegend": False, }],
        "title": {
            "text": "Number of stop-searches in "+str(pfaName_ops)+", " + str(year_ops[0])+"-" + str(year_ops[1]),
            'align': 'left',
            'style': {
                'fontSize': '18px', 'fontWeight': '300px'}},
        'plotOptions': {'series': {'color': '#E10000ED'}},
        'tooltip': {
            'shared': True,
            'useHTML': True,
            'formatter': "function () {\
               return '<small>'+ this.x +'</small><br />Number of stop-searches: <b>' + Highcharts.numberFormat(this.y,0,',',',') + '</b>'\
                   }"
        }
    }
    plot = ph.HighChart(object=plot, sizing_mode='stretch_width', height=270)
    return plot

# 3.2. - Stop and search incidence by ethnicity bars for selected PFA for time interval
# ----------------------------------------------------------------------------------------


@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def plot_bar_eth_prop(year_ops, pfaName_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    dfPFA_ops = create_dfPFA_ops_eth_agg(
        dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops)
    dfPFA_bar_eth_prop = dfPFA_ops
    dfPFA_bar_eth_prop['rateOfSearch'] = round(((
        dfPFA_bar_eth_prop['numberOfSearches'] / dfPFA_bar_eth_prop[pop])*100)*1000, 1)
    dfPFA_bar_eth_prop.replace([np.inf, -np.inf], np.nan, inplace=True)
    dfPFA_bar_eth_prop = dfPFA_bar_eth_prop[dfPFA_bar_eth_prop["selfDefinedEthnicityGroup"].str.contains(
        "Unknown") == False]
    plot = {
        "chart": {"type": "bar", 'backgroundColor': '#1A1A1A'},
        "xAxis": {
            "categories": dfPFA_bar_eth_prop['selfDefinedEthnicityGroup']},
        "yAxis": {
            'gridLineWidth': '.25', 'title': {'enabled': False}},
        "series": [{
            'name': 'Rate of stop and search per 1,000 people', "data": dfPFA_bar_eth_prop['rateOfSearch'], "showInLegend": False, }],
        "title": {
            "text": "Rate of stop and search per 1,000 people by ethnicity in\n" + str(pfaName_ops) + ", "+str(year_ops[0])+"-"+str(year_ops[1]),
            'align': 'left',
            'style': {
                'fontSize': '18px', 'fontWeight': '300px'}},
        'plotOptions': {'series': {'color': '#E10000ED', 'borderColor': '#E10000'},
                        'dataLabels': {'enabled': True, 'y': 1, 'style': {'fontWeight': 'bold', 'fontSize': '14.5px'}}
                        },
        'tooltip': {
            'shared': True,
            'useHTML': True,
            'formatter': "function () {\
           return '<small>'+ this.x +'</small><br />Stop-search rate per 1,000 people: <b>' + Highcharts.numberFormat(this.y,0,',',',') + '</b>'\
               }"

        }
    }
    plot = ph.HighChart(object=plot, height=270, width=460)
    return plot


# 3.4. - Number stop and search for selected PFA versus other PFA across time interval
# -----------------------------------------------------------------------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def plot_tsscatter(year_ops, pfaName_ops, legislation_opss, population_ops):
    dfPFA_tsscatter = create_dfPFA_ops_agg_pop_ts(
        dfPFA, year_ops, pfaName_ops, legislation_opss, population_ops)
    dfPFA_tsscatter = dfPFA_tsscatter.drop(columns=['numberOfSearches'])
    dfPFA_tsscatter_wide = dfPFA_tsscatter.pivot(
        index='year', columns='pfaName', values='rateOfSearch').reset_index()
    dfPFA_tsscatter_main = dfPFA_tsscatter_wide[['year', pfaName_ops]]
    dfPFA_tsscatter_other = dfPFA_tsscatter_wide.drop(columns=[pfaName_ops])
    listPFAseries = []
    # add line that varies jitter by number of years
    for col in dfPFA_tsscatter_other.loc[:, dfPFA_tsscatter_other.columns != 'year']:
        x = (-0.3/11)*((year_ops[1]-year_ops[0])+1)
        y = (-0.15/11)*((year_ops[1]-year_ops[0])+1)
        xNoise = rnd.uniform(x, abs(x))
        yNoise = rnd.uniform(y, abs(y))
        listPFAseries.append({'name': col, 'color': '#d3d3d399', 'borderColor': '#d3d3d3', "data": dfPFA_tsscatter_other[col], 'marker': {
                             'enabled': True, 'symbol': "circle", 'radius': 2.5}, 'jitter': {'x': xNoise, 'y': yNoise}, "showInLegend": False},)
    listPFAseries.append({'name': pfaName_ops, 'color': '#E10000ED', 'borderColor': '#E10000', "data": dfPFA_tsscatter_main[pfaName_ops], 'marker': {
                         'enabled': True, 'symbol': "circle", 'radius': 10}, "showInLegend": False},)
    if pfaName_ops != 'Metropolitan Police':
        yMax = dfPFA_tsscatter[dfPFA_tsscatter['pfaName']
                               != 'Metropolitan Police']['rateOfSearch'].max()
    else:
        yMax = dfPFA_tsscatter['rateOfSearch'].max()
    plot = {
        "chart": {"type": "scatter", 'backgroundColor': '#1A1A1A', 'inverted': True},
        "xAxis": {'categories': dfPFA_tsscatter_main['year'].astype('str')},
        "yAxis": {
            'gridLineWidth': '.25', 'title': {'enabled': False}, 'max': yMax},
        "series": listPFAseries,
        "title": {
            "text": "Rate of stop and search per 1,000 people in " + str(pfaName_ops) + " compared to other PFAs, "+str(year_ops[0])+"-"+str(year_ops[1]),
            'align': 'left',
            'style': {
                'fontSize': '18px', 'fontWeight': '300px'}},
        'plotOptions': {'series': {'color': '#E1000066'}},
        'tooltip': {
            'shared': True, 'useHTML': True,
            'formatter': "function () {\
              return '<small>'+this.series.name+', '+ this.x +'</small><br />Stop and search rate per 1,000 people: <b>' + Highcharts.numberFormat(this.y, 0) + '</b>'\
         }"
        }
    }
    plot = ph.HighChart(object=plot, sizing_mode="fixed",
                        height=600, width=460)
    return plot


# 3.5.
# ------------------------
@pn.depends(year_ops, legislation_ops, population_ops)
def plot_bar_odds_ratio_UK(year_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    df = create_dfPFA_ops_agg_eth_uk(dfPFA, year_ops, legislation_ops, population_ops)
    df['rateOfSearches'] = ((df['numberOfSearches'] / df[pop])*100)
    ethnicity_index = df['selfDefinedEthnicityGroup'].values
    df.set_index(ethnicity_index, inplace=True)
    df = df.loc[['White', 'Asian', 'Black', 'Mixed', 'Other Ethnic Group'], :]
    df['ratios'] = [round(i/df['rateOfSearches']['White'], 2)
                    for i in df['rateOfSearches']]
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    #df['index'] = 1
    #df = df.pivot(index='index', columns=['selfDefinedEthnicityGroup'], values='ratios')
    plot = {
        'chart': {"type": "bar", 'backgroundColor': '#1A1A1A'},
        'xAxis': {'categories': df['selfDefinedEthnicityGroup']},
        'yAxis': {'gridLineWidth': '.25', 'title': {'enabled': False}},
        'series': [
            {'name': 'Odds of stop and search relative to people of white ethnicity',
                "data": df['ratios'], "showInLegend": False, 'colorByPoint':True},
        ],
        'title': {
            'text': "Ethnic disparities in stop and search (odds ratios) in England and Wales, " + str(year_ops[0])+"-"+str(year_ops[1]),
            'align': 'left',
            'style': {
                'fontSize': '18px', 'fontWeight': '300px'}},
        'plotOptions': {'series': {'colors': ['#d3d3d3D9', '#E10000ED', '#E10000ED', '#E10000ED', '#E10000ED'],
                                   'borderColor': ['#d3d3d3', '#E10000', '#E10000', '#E10000', '#E10000'],
                                   'dataLabels': {'enabled': False, "inside": False, 'x': 5, 'y': 2, 'style': {'fontWeight': 'bold', 'fontSize': '14.5px'}}}},
        'tooltip': {
            'shared': True,
            'useHTML': True,
            'formatter': "function () {\
          return '<small>'+ this.x +'</small><br />Stop-search odds relative to white ethnicity: <b>' + Highcharts.numberFormat(this.y,2) + '</b>'\
              }"

        }
    }
    plot = ph.HighChart(object=plot, sizing_mode='fixed',
                        height=270, width=570)
    return plot


# 3.5.
# ------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def plot_bar_odds_ratio_PFA(year_ops, pfaName_ops, legislation_ops, population_ops):
    if population_ops == 'Unadjusted (carried-forward census values)':
       pop = 'population'
    else:
       pop = 'populationIpol'
    df = create_dfPFA_ops_eth_agg(
        dfPFA, year_ops, pfaName_ops, legislation_ops, population_ops)
    df['rateOfSearches'] = ((df['numberOfSearches'] / df[pop])*100)
    ethnicity_index = df['selfDefinedEthnicityGroup'].values
    df.set_index(ethnicity_index, inplace=True)
    df = df.loc[['White', 'Asian', 'Black', 'Mixed', 'Other Ethnic Group'], :]
    df['ratios'] = [round(i/df['rateOfSearches']['White'], 2)
                    for i in df['rateOfSearches']]
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    plot = {
        'chart': {"type": "bar", 'backgroundColor': '#1A1A1A'},
        'xAxis': {'categories': df['selfDefinedEthnicityGroup']},
        'yAxis': {'gridLineWidth': '.25', 'title': {'enabled': False}},
        'series': [
            {'name': 'Odds of stop and search relative to white ethnicity',
                "data": df['ratios'], "showInLegend": False, 'colorByPoint':True},
        ],
        'title': {
            'text': "Ethnic disparities in stop and search (odds ratios) in "+str(pfaName_ops) + ", "+str(year_ops[0])+"-"+str(year_ops[1]),
            'align': 'left',
            'style': {
                'fontSize': '18px', 'fontWeight': '300px'}},
        'plotOptions': {'series': {'colors': ['#d3d3d3D9', '#E10000ED', '#E10000ED', '#E10000ED', '#E10000ED'],
                                   'borderColor': ['#d3d3d3', '#E10000', '#E10000', '#E10000', '#E10000'],
                                   'dataLabels': {'enabled': False, "inside": False, 'x': 5, 'y': 2, 'style': {'fontWeight': 'bold', 'fontSize': '14.5px'}}}},
        'tooltip': {
            'shared': True,
            'useHTML': True,
            'formatter': "function () {\
          return '<small>'+ this.x +'</small><br />Stop-search odds relative white ethnicity: <b>' + Highcharts.numberFormat(this.y,2) + '</b>'\
              }"
        }
    }
    plot = ph.HighChart(object=plot, sizing_mode='fixed',
                        height=270, width=570)
    return plot


# 3.6. - Police Force Area map
# -----------------------------------------------------------------------------------------
@pn.depends(year_ops, pfaName_ops, legislation_ops, population_ops)
def map_pfa(year_ops, pfaName_ops, legislation_ops, population_ops):

    # Load options dataframe and add geometries
    df = create_dfPFA_ops_agg_pop(dfPFA, year_ops, legislation_ops, population_ops)
    dfBounds = pd.merge(boundsPFA, df[['pfaName', 'numberOfSearches']],
                        left_on='name', right_on='pfaName', how='left')
    # Mapping for map plot options
    mapOps = dfBounds.loc[dfBounds['pfaName'] !=
                          'Metropolitan Police', ['pfaName', 'numberOfSearches']]
    tempMet = dfBounds.loc[dfBounds['pfaName'] ==
                           'Metropolitan Police', ['pfaName', 'numberOfSearches']]
    mapOps['elevation'] = (mapOps['numberOfSearches'] - np.min(mapOps['numberOfSearches'])) / \
        (np.max(mapOps['numberOfSearches']) -
         np.min(mapOps['numberOfSearches']))
    mapOps = pd.merge(mapOps, tempMet, on=[
                      'pfaName', 'numberOfSearches'], how='outer')
    mapOps['elevation'] = np.where(mapOps['pfaName'] == 'Metropolitan Police', mapOps.sort_values(
        "elevation", ascending=False)['elevation'].iloc[0]*1.95, mapOps['elevation'])
    mapOps['decile'] = pd.qcut(mapOps['numberOfSearches'], 10, labels=False)
    colorsR = [i*.9 for i in [255, 254, 253,
                              253, 252, 243, 225, 208, 190, 173]]
    colorsG = [i*.9 for i in [247, 228, 209, 190, 171, 144, 108, 72, 36, 0]]
    colorsB = [i*.9 for i in [236, 207, 179, 151, 123, 96, 72, 48, 24, 0]]
    mapOps['fillR'] = 0
    mapOps['fillG'] = 0
    mapOps['fillB'] = 0
    for i in range(len(mapOps)): # I CHANGED BELOW
        d = mapOps['decile'].iloc[i]
        mapOps.iloc[i, mapOps.columns.get_loc('fillR')] = colorsR[d]
        mapOps.iloc[i, mapOps.columns.get_loc('fillG')] = colorsG[d]
        mapOps.iloc[i, mapOps.columns.get_loc('fillB')] = colorsB[d]
    # Add plot option mapping to main dataframe
    dfBoundsOps = pd.merge(dfBounds, mapOps[[
                           'pfaName', 'elevation', 'decile', 'fillR', 'fillG', 'fillB']], on='pfaName', how='left')
    dfBoundsOps['numberOfSearches'] = dfBoundsOps['numberOfSearches'].apply(
        lambda d: f'{round(d, 2):,}')
    if pfaName_ops in ['Hertfordshire', 'Bedfordshire', 'Northamptonshire']:
        dfBoundsOps['elevation'] = np.where(
            dfBoundsOps['pfaName'] == 'Metropolitan Police', 0, dfBoundsOps['elevation'])

    dfBoundsOps_pfa = dfBoundsOps[dfBoundsOps['pfaName'] == pfaName_ops]
    # CHANGED HERE TOO
    pfa_lng = float(dfBoundsOps_pfa.centroid.x)
    pfa_lat = float(dfBoundsOps_pfa.centroid.y)
    pfa_col = {'lng': pfa_lng , 
         'lat': pfa_lat, 
         "ele": dfBoundsOps_pfa['elevation'].iloc[0]+1.5
    }
    pfa_col_df = pd.DataFrame(data=pfa_col, index=[0])
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=pfa_col_df,
        get_position=['lng', 'lat'],
        get_elevation="ele",
        elevation_scale=50000,
        radius=6500,
        get_fill_color=[211, 211, 211, 250],
        #get_fill_color=[253, 231, 37, 180],
        #####get_fill_color=[0, 173, 236, 150],
        #get_fill_color=[87, 236,0, 150],
        ########## get_fill_color=[24, 156, 205, 180],
        #get_fill_color=[253, 231, 37, 150],
        #get_fill_color=[0, 173,0, 150],
        pickable=False,
        auto_highlight=False,
    )

    polygon_3d = pdk.Layer(
        "GeoJsonLayer",
        dfBoundsOps,
        wireframe=True,
        get_fill_color="[fillR, fillG, fillB]",
        #get_line_color="[fillR, fillG, fillB]",
        get_line_color=[50, 50, 50],
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
    deckMap = pdk.Deck(layers=[polygon_3d, column_layer],
                       initial_view_state=view_state, tooltip=tooltip)
    map_pane = pn.pane.DeckGL(deckMap, height=585, width=690)
    return map_pane


@pn.depends(year_ops, pfaName_ops, legislation_ops)
def map_pfa_title(year_ops, pfaName_ops, legislation_ops):
    title_html = pn.pane.Markdown('Number of stop-searches in '+str(pfaName_ops) + ' compared to other PFAs, '+str(year_ops[0])+"-"+str(year_ops[1]),
                                  style={"font-family": "Lucida Sans Unicode", "color": "white", 'font-size': '18px', 'font-weight': '300px', 'background-color': '#2C353C', 'border-radius': '0px', "padding-left": "15px"}, margin=(0, 0, -9, -9))
    return title_html
# 181818

###################################################################################


###############################################################################
#logo = pn.panel('stopwatch_logo.png', width=250, align='start')


#def image_to_data_url(filename):
#    ext = filename.split('.')[-1]
#    prefix = f'data:image/{ext};base64,'
#    with open(filename, 'rb') as f:
#        img = f.read()
#    return prefix + base64.b64encode(img).decode('utf-8')


#logo2 = image_to_data_url('stopwatch_logo.png')
#logo2 = image_to_data_url('stopwatch_logo.png')

#one = pn.widgets.Button(name='Overview', width=50, button_type='primary', height = 35)
#two = pn.widgets.Button(name='Ethnic Disparities', width=50, button_type='primary', height = 35)
# toggle_group = pn.widgets.ToggleGroup(name='ToggleGroup', options=['Overview', 'Ethnic Disparities'],
# behavior="radio", height = 35)

further_ops_pane = pn.pane.HTML("""
Additional options
""", style={'background-color': '#181818', 'border': '#181818', 'padding-left': '6px'})
checkbox = pn.widgets.Checkbox(name='<b>Use adjusted population estimates</b>')
colorpicker = pn.Row(
    pn.Column(pn.widgets.ColorPicker(value='#d3d3d3'), width=100, height=5),
    pn.Column(pn.pane.HTML("""Change map marker colour""")),
    css_classes=['panel-widget-boxx'])

# Further options
# Use adjusted population estimates
# Change map marker color


# Key statistics   # Technical notes
# 181818


# html_pane.style = dict(html_pane.style, border='2px solid #202020')


# same as title

# , favicon = logo2
template = pn.template.FastGridTemplate(theme="dark",
                                        site="", title="Interactive stop and search tracker",
                                        sidebar=[pn.Spacer(
                                            height=15), main_ops_pane, pn.Spacer(
                                            height=15), footer_pane],
                                        sidebar_width=410, header_background='#130C16',
                                        header_neutral_color='#D9D9D9', accent_base_color='#D9D9D9', corner_radius=6, shadow=True,
                                        # , cols = {'lg': 18, 'md': 12, 'sm': 8, 'xs': 6, 'xxs': 4}
                                        prevent_collision=True, theme_toggle=False
                                        )


# neutral_color = ,
#  background_color = '#130C16'
template.main[:2, :7] = plot_num_tsline
template.main[:2, 7:12] = plot_bar_eth_prop
template.main[2:6, :7] = pn.Column(map_pfa_title, map_pfa)
template.main[2:6, 7:12] = plot_tsscatter
template.main[6:8, :6] = plot_bar_odds_ratio_UK
template.main[6:8, 6:12] = plot_bar_odds_ratio_PFA

template.servable()


# populate factsheet + write out reference notes
# Get population denominator widget running
# Drop Section 44/47
# Ensure legislation functionality on all plots
# sort out missing Devon observations
# consider Met wording
