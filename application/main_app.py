# -*- coding: utf-8 -*-
"""
Created on Tue Feb 21 22:08:26 2023

@author: MatthewTibbles
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.figure import Figure
import panel as pn
import folium as fm
import hvplot.pandas
import holoviews as hv
import plotly
import bokeh.io
from bokeh.models import Title
from bokeh.models import LabelSet
from bokeh.models import ColumnDataSource
hv.extension('bokeh')
#hv.extension('plotly')



#year = pn.widgets.IntRangeSlider(name=’Select year’, width=250, start=2011, end=201, value=(2011, 2021), value_throttled=(1985, 2016))


# Loading Data
dfPFA = pd.read_csv('dfPFA_clean.csv')
#dfPFA = pd.read_csv(r"C:\Users\MatthewTibbles\Downloads\dfPFA_clean.csv")

# Bar chart
#@pn.depends(year.param.value_throttled)
#def plot_bar(year):
 #   years_df = df[df.Began.dt.year.between(year[0], year[1])]
 #   bar_table = years_df[“MainCause”]
#     .value_counts()
#     .reset_index()
 #    .rename(columns={“index”:’Cause’, “MainCause”:”Total”})
#    return bar_table[:10].sort_values(“Total”)
 #    .hvplot.barh(“Cause”, “Total”, 
 #      invert=False, legend=’bottom_right’, height=600)


#==============================================================================
#                             1. Widgets                             #                                
#==============================================================================

# Year range slider
startYear = dfPFA.year.min().astype('int').item()
endYear = dfPFA.year.max().astype('int').item()
year_ops = pn.widgets.IntRangeSlider(
    name='What year(s) would like to visualise?',
    start=startYear, end=endYear, 
    value=(startYear, endYear), value_throttled=(startYear, endYear),
    step=1, bar_color = '#E10000')

# PFA area drop down list
pfaName_list = dfPFA.pfaName.unique().tolist()
pfaName_ops = pn.widgets.Select(name='What Police Force Area (PFA) would you like to visualise?', options=pfaName_list)

# Legislation drop down list
legislation_list = dfPFA.legislation.unique().tolist()
legislation_ops = pn.widgets.Select(name='Which legislation would like to visualise?', options=legislation_list)


#==============================================================================
#                             2. Function to create options based dataframe                            
#==============================================================================

@pn.depends(year_ops,pfaName_ops, legislation_ops)
def create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['pfaName'] == pfaName_ops]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_ops = dfPFA_ops.groupby(['year','pfaName', 'legislation', 'selfDefinedEthnicityGroup'], as_index = False)[[
      'numberOfSearches', 'population']].sum()
   #dfPFA_ops['selfDefinedEthnicityGroup'] = dfPFA_ops[
   #   'selfDefinedEthnicityGroup'].astype('category')
   #dfPFA_ops['selfDefinedEthnicityGroup'].cat.reorder_categories([
   #   'White', 'Black', 'Mixed', 'Asian', 'Other Ethnic Group', 'Not Stated / Unknown'])
   return(dfPFA_ops)

#==============================================================================
#                             3. Function for summary text                         #                                
#==============================================================================

@pn.depends(year_ops,pfaName_ops, legislation_ops)
def summary_text(year_ops,pfaName_ops, legislation_ops):
   dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
   totalSearches = sum(dfPFA_ops['numberOfSearches'])
   return '##### {totalSearches} people were stopped and searched by police in {pfaName} between {startYear} and {endYear} under {legislation}.'.format(
      totalSearches=totalSearches, pfaName = pfaName_ops,
      startYear=year_ops[0],endYear=year_ops[1], legislation = legislation_ops)

#==============================================================================
#                             3. Plot function                            #                                
#==============================================================================
#from bokeh.io import curdoc
#curdoc().theme = 'night_sky'
# Time series line
@pn.depends(year_ops,pfaName_ops, legislation_ops)
def plot_tsline(year_ops,pfaName_ops, legislation_ops):
   dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
   dfPFA_tsline = dfPFA_ops.groupby(['year','pfaName', 'legislation'],as_index=False).sum()
   dfPFA_tsline['year'] = dfPFA_tsline['year'].astype('str')
   
   border_fill_hook = lambda p, _: p.state.update(border_fill_alpha=1)
   outer_line_hook = lambda p, _: p.state.update(outline_line_color=None)
   yaxis_line_hook = lambda p, _: p.handles['yaxis'].update(axis_line_color=None)
   xaxis_line_hook = lambda p, _: p.handles['xaxis'].update(axis_line_color=None)
   yaxis_mintick_hook = lambda p, _: p.handles['yaxis'].update(major_tick_line_color=None)
   yaxis_majtick_hook = lambda p, _: p.handles['yaxis'].update(minor_tick_line_color = None)
   hook_ops = [border_fill_hook, outer_line_hook, yaxis_line_hook,xaxis_line_hook,
               yaxis_mintick_hook,  yaxis_majtick_hook]
   
   hv_plotOut_line = dfPFA_tsline.sort_values('year').hvplot.line(
      x='year',y='numberOfSearches', color=hv.Cycle(['#E10000']), ylim=[0,None],
      height=250, xlabel = "", ylabel = "", yaxis = None, width = 700).opts(hooks=hook_ops)
   hv_plotOut_scatter = dfPFA_tsline.sort_values('year').hvplot.scatter(
   x='year',y='numberOfSearches', color=hv.Cycle(['#E10000']), ylim=[0,None], yaxis = None,
   height=250, width = 700).opts(color='#E10000', size=8, marker='o',hooks=hook_ops) #* \
   hv_plotOut = hv_plotOut_line * hv_plotOut_scatter 
   bk_plotOut =  hv.render(hv_plotOut)
   dfPFA_tsline['lab'] = dfPFA_tsline['numberOfSearches'].astype('str')
   source = ColumnDataSource(dict(
    percent=dfPFA_tsline['numberOfSearches'],count=dfPFA_tsline['year'], labels=dfPFA_tsline['lab']))
   labels = LabelSet(x='count', y='percent', text='labels',text_color = "white",
         x_offset=-17, y_offset=-22.5, text_font_size = '10px', source=source)
   bk_plotOut.add_layout(labels)
   bk_plotOut.add_layout(Title(text="Number of stop and search incidents in "+str(pfaName_ops)+", " +str(year_ops[1])+"-" +str(year_ops[0]), text_font_size="12pt", text_font_style="bold"), 'above')
   bk_plotOut.toolbar.autohide = True  
   #bk_plotOut.add_layout(Title(text='Ethnic disparities in stop and search '+str(pfaName_ops)+', '+str(legislation_ops), text_font_size="16pt", text_font_style="bold"), 'above')
   return bk_plotOut
   

# scatter
@pn.depends(year_ops,pfaName_ops, legislation_ops)
def plot_tsscatter(year_ops,pfaName_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_tsscatter = dfPFA_ops.groupby(['year','pfaName', 'legislation'], as_index = False)[[
      'numberOfSearches']].sum()
   dfPFA_tsscatter = dfPFA_tsscatter.groupby(
      ['year', 'pfaName', 'legislation'],as_index=False)[
          ['numberOfSearches']].agg({'numberOfSearches':'sum'})
   dfPFA_tsscatter['year'] = dfPFA_tsscatter['year'].astype('str')
   #print(pfaName_ops)
   dfPFA_tsscatter['size'] = np.where(dfPFA_tsscatter['pfaName'] == pfaName_ops, 250, 15)
   dfPFA_tsscatter['color'] = np.where(dfPFA_tsscatter['pfaName'] == pfaName_ops, '#E10000', '#d3d3d399')
   dfPFA_tsscatter['alpha'] = np.where(dfPFA_tsscatter['pfaName'] == pfaName_ops, 1, 25)
   #print(dfPFA_tsscatter['size'])
   #dfPFA_tsscatter['year'] = dfPFA_tsscatter['year'].astype('str')
   #dfPFA_tsscatter['year'] = str(year_ops[0])
   border_fill_hook = lambda p, _: p.state.update(border_fill_alpha=1)
   outer_line_hook = lambda p, _: p.state.update(outline_line_color=None)
   yaxis_line_hook = lambda p, _: p.handles['yaxis'].update(axis_line_color=None)
   xaxis_line_hook = lambda p, _: p.handles['xaxis'].update(axis_line_color=None)
   xaxis_mintick_hook = lambda p, _: p.handles['xaxis'].update(minor_tick_line_color = None)
   hook_ops = [border_fill_hook, outer_line_hook,yaxis_line_hook,xaxis_line_hook,
              xaxis_mintick_hook]
   hv_plotOut = dfPFA_tsscatter.hvplot.scatter(
      x='year',y='numberOfSearches', invert = True , toolbar_location=None, size = 'size', xlabel = "", ylabel = "", color='color', ylim=[0,60000],
      height=700, width = 490).opts(jitter=.45, hooks = hook_ops)
   bk_plotOut =  hv.render(hv_plotOut)
   bk_plotOut.add_layout(Title(text="Number of stop and search incidents in\n" +str(pfaName_ops) + " versus all other PFAs, "+str(year_ops[0])+"-"+str(year_ops[1]), text_font_size="12pt", text_font_style="bold"), 'above')   #color=hv.Cycle(['#E10000','#130C16','#130C16','#130C16','#130C16','#130C16']),
   bk_plotOut.toolbar.autohide = True  
   #xlim=[0,None], legend = False, stacked=False, height=250, width = 490).opts(hooks=[lambda p, _: p.state.update(border_fill_alpha=0)])
  # bk_plotOut =  hv.render(hv_plotOut)
   #bk_plotOut.add_layout(Title(text="Stop and search incidence rate per 1,000 people in\n" + str(pfaName_ops), text_font_size="12pt", text_font_style="bold"), 'above')
   #bk_plotOut.add_layout(Title(text='Ethnic disparities in stop and search '+str(pfaName_ops)+', '+str(legislation_ops),text_font_size="16pt", text_font_style="bold"), 'above')
   return bk_plotOut




# Incidence rate bars (think this should probably be odds ratios but whatever 4now)
@pn.depends(year_ops,pfaName_ops, legislation_ops)
def plot_bar_eth_prop(year_ops,pfaName_ops, legislation_ops):
   dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
   dfPFA_bar_eth_prop = dfPFA_ops.groupby(
      ['pfaName', 'legislation', 'selfDefinedEthnicityGroup'],as_index=False)[
          ['numberOfSearches','population']].agg({'numberOfSearches':'sum','population':'sum'})
   dfPFA_bar_eth_prop['rateOfSearches'] = round(((
      dfPFA_bar_eth_prop['numberOfSearches'] / dfPFA_bar_eth_prop['population'])*100)*1000,1)
   dfPFA_bar_eth_prop.replace([np.inf, -np.inf], np.nan, inplace=True)
   #print(dfPFA_bar_eth_prop)
   border_fill_hook = lambda p, _: p.state.update(border_fill_alpha=1)
   outer_line_hook = lambda p, _: p.state.update(outline_line_color=None)
   yaxis_line_hook = lambda p, _: p.handles['yaxis'].update(axis_line_color=None)
   xaxis_line_hook = lambda p, _: p.handles['xaxis'].update(axis_line_color=None)
   yaxis_mintick_hook = lambda p, _: p.handles['yaxis'].update(major_tick_line_color=None)
   yaxis_majtick_hook = lambda p, _: p.handles['yaxis'].update(minor_tick_line_color = None)
   hook_ops = [border_fill_hook, outer_line_hook, yaxis_line_hook,xaxis_line_hook,
               yaxis_mintick_hook,  yaxis_majtick_hook]
   hv_plotOut = dfPFA_bar_eth_prop.hvplot.bar(
      x='selfDefinedEthnicityGroup',y='rateOfSearches',
      color=hv.Cycle(['#E10000','#130C16','#130C16','#130C16','#130C16','#130C16']),
      xlim=[0,None], yaxis = None, xlabel = "", legend = False, stacked=False, height=250, width = 490).opts(hooks=[lambda p, _: p.state.update(hooks = hook_ops)])
   bk_plotOut =  hv.render(hv_plotOut)
   dfPFA_bar_eth_prop['lab'] = dfPFA_bar_eth_prop['rateOfSearches'].astype('str')
   source = ColumnDataSource(dict(
    rates=dfPFA_bar_eth_prop['rateOfSearches'],ethnicity=dfPFA_bar_eth_prop['selfDefinedEthnicityGroup'], labels=dfPFA_bar_eth_prop['lab']))
   labels = LabelSet(x='ethnicity', y='rates', text='labels',text_color = "white",
                     y_offset=10, x_offset =-11.5, text_font_size = '14px', source=source)
   bk_plotOut.add_layout(labels)
   bk_plotOut.add_layout(Title(text="Stop and search incidence rate per 1,000 people in\n" + str(pfaName_ops) +", "+str(year_ops[0])+"-"+str(year_ops[1]), text_font_size="12pt", text_font_style="bold"), 'above')
   bk_plotOut.toolbar.autohide = True
   return bk_plotOut

@pn.depends(year_ops,pfaName_ops,legislation_ops)
def plot_bar_odds_ratio_UK(year_ops, pfaName_ops, legislation_ops):
   dfPFA_ops = dfPFA[dfPFA['year'].between(year_ops[0],year_ops[1], inclusive='both')]
   dfPFA_ops = dfPFA_ops[dfPFA_ops ['legislation'] == legislation_ops]
   dfPFA_bar_odds_ratio_UK = dfPFA_ops.groupby(
      ['legislation', 'selfDefinedEthnicityGroup'],as_index=False)[
          ['numberOfSearches','population']].agg({'numberOfSearches':'sum','population':'sum'})
   dfPFA_bar_odds_ratio_UK['rateOfSearches'] = ((
      dfPFA_bar_odds_ratio_UK['numberOfSearches'] / dfPFA_bar_odds_ratio_UK['population'])*100)
   ethnicity_index = dfPFA_bar_odds_ratio_UK['selfDefinedEthnicityGroup'].values
   dfPFA_bar_odds_ratio_UK.set_index(
       ethnicity_index, inplace = True)
   dfPFA_bar_odds_ratio_UK = dfPFA_bar_odds_ratio_UK.loc[
       ['White', 'Asian', 'Black', 'Mixed', 
        'Other Ethnic Group', 'Not Stated / Unknown'], :]
   dfPFA_bar_odds_ratio_UK['ratios'] = [round(i/dfPFA_bar_odds_ratio_UK['rateOfSearches']['White'], 2) for i in dfPFA_bar_odds_ratio_UK['rateOfSearches']]
   dfPFA_bar_odds_ratio_UK.replace([np.inf, -np.inf], np.nan, inplace=True)
   dfPFA_bar_odds_ratio_UK = dfPFA_bar_odds_ratio_UK[dfPFA_bar_odds_ratio_UK.selfDefinedEthnicityGroup != 'Not Stated / Unknown']
   dfPFA_bar_odds_ratio_UK['color'] = np.where(
       dfPFA_bar_odds_ratio_UK['selfDefinedEthnicityGroup'] == 'White', '#d3d3d399', '#E10000')
   
   border_fill_hook = lambda p, _: p.state.update(border_fill_alpha=1)
   outer_line_hook = lambda p, _: p.state.update(outline_line_color=None)
   yaxis_line_hook = lambda p, _: p.handles['yaxis'].update(axis_line_color=None)
   xaxis_line_hook = lambda p, _: p.handles['xaxis'].update(axis_line_color=None)
   yaxis_mintick_hook = lambda p, _: p.handles['yaxis'].update(major_tick_line_color=None)
   yaxis_majtick_hook = lambda p, _: p.handles['yaxis'].update(minor_tick_line_color = None)
   hook_ops = [border_fill_hook, outer_line_hook, yaxis_line_hook,xaxis_line_hook,
               yaxis_mintick_hook,  yaxis_majtick_hook]
   dfPFA_bar_odds_ratio_UK['selfDefinedEthnicityGroup'] =  dfPFA_bar_odds_ratio_UK['selfDefinedEthnicityGroup'].astype('str')
   
   ylims = (dfPFA_bar_odds_ratio_UK['ratios'].max())+1
   hv_plotOut = dfPFA_bar_odds_ratio_UK.hvplot.bar(
      x='selfDefinedEthnicityGroup',y='ratios',
      color= 'color', xlabel = "",ylim=[0,ylims], yaxis = None, 
      legend = False, stacked=False, height=250, width = 700).opts(fontsize={'labels': 12,},hooks=hook_ops)
   bk_plotOut =  hv.render(hv_plotOut)
   dfPFA_bar_odds_ratio_UK['lab'] = dfPFA_bar_odds_ratio_UK['ratios'].astype('str')
   source = ColumnDataSource(dict(
    ratios=dfPFA_bar_odds_ratio_UK['ratios'],ethnicity=dfPFA_bar_odds_ratio_UK['selfDefinedEthnicityGroup'], labels=dfPFA_bar_odds_ratio_UK['lab']))
   labels = LabelSet(x='ethnicity', y='ratios', text='labels',text_color = "white",
                     y_offset=10, x_offset =-11.5, text_font_size = '14px', source=source)
   bk_plotOut.add_layout(labels)
   bk_plotOut.add_layout(Title(text="Odds of a person being stop and searched relative to a person of white ethnicity in\nEngland and Wales, " +str(year_ops[0])+"-"+str(year_ops[1]), text_font_size="12pt", text_font_style="bold"), 'above')
   bk_plotOut.toolbar.autohide = True
   return bk_plotOut


@pn.depends(year_ops,pfaName_ops,legislation_ops)
def plot_bar_odds_ratio_pfa(year_ops, pfaName_ops, legislation_ops):
   dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
   dfPFA_bar_odds_ratio_pfa = dfPFA_ops.groupby(
      ['pfaName', 'legislation', 'selfDefinedEthnicityGroup'],as_index=False)[
          ['numberOfSearches','population']].agg({'numberOfSearches':'sum','population':'sum'})
   dfPFA_bar_odds_ratio_pfa['rateOfSearches'] = ((
      dfPFA_bar_odds_ratio_pfa['numberOfSearches'] / dfPFA_bar_odds_ratio_pfa['population'])*100)
   ethnicity_index = dfPFA_bar_odds_ratio_pfa['selfDefinedEthnicityGroup'].values
   dfPFA_bar_odds_ratio_pfa.set_index(
       ethnicity_index, inplace = True)
   dfPFA_bar_odds_ratio_pfa = dfPFA_bar_odds_ratio_pfa.loc[
       ['White', 'Asian', 'Black', 'Mixed', 
        'Other Ethnic Group', 'Not Stated / Unknown'], :]
   dfPFA_bar_odds_ratio_pfa['ratios'] = [round(i/dfPFA_bar_odds_ratio_pfa['rateOfSearches']['White'], 2) for i in dfPFA_bar_odds_ratio_pfa['rateOfSearches']]
   dfPFA_bar_odds_ratio_pfa.replace([np.inf, -np.inf], np.nan, inplace=True)
   dfPFA_bar_odds_ratio_pfa = dfPFA_bar_odds_ratio_pfa[dfPFA_bar_odds_ratio_pfa.selfDefinedEthnicityGroup != 'Not Stated / Unknown']
   dfPFA_bar_odds_ratio_pfa['color'] = np.where(
       dfPFA_bar_odds_ratio_pfa['selfDefinedEthnicityGroup'] == 'White', '#d3d3d399', '#E10000')
   
   border_fill_hook = lambda p, _: p.state.update(border_fill_alpha=1)
   outer_line_hook = lambda p, _: p.state.update(outline_line_color=None)
   yaxis_line_hook = lambda p, _: p.handles['yaxis'].update(axis_line_color=None)
   xaxis_line_hook = lambda p, _: p.handles['xaxis'].update(axis_line_color=None)
   yaxis_mintick_hook = lambda p, _: p.handles['yaxis'].update(major_tick_line_color=None)
   yaxis_majtick_hook = lambda p, _: p.handles['yaxis'].update(minor_tick_line_color = None)
   hook_ops = [border_fill_hook, outer_line_hook, yaxis_line_hook,xaxis_line_hook,
               yaxis_mintick_hook,  yaxis_majtick_hook]
   dfPFA_bar_odds_ratio_pfa['selfDefinedEthnicityGroup'] =  dfPFA_bar_odds_ratio_pfa['selfDefinedEthnicityGroup'].astype('str')
   
   ylims = (dfPFA_bar_odds_ratio_pfa['ratios'].max())+1
   hv_plotOut = dfPFA_bar_odds_ratio_pfa.hvplot.bar(
      x='selfDefinedEthnicityGroup',y='ratios',
      color= 'color', xlabel = "",ylim=[0,ylims], yaxis = None, 
      legend = False, stacked=False, height=250, width = 490).opts(fontsize={'labels': 12,},hooks=hook_ops)
   bk_plotOut =  hv.render(hv_plotOut)
   dfPFA_bar_odds_ratio_pfa['lab'] = dfPFA_bar_odds_ratio_pfa['ratios'].astype('str')
   source = ColumnDataSource(dict(
    ratios=dfPFA_bar_odds_ratio_pfa['ratios'],ethnicity=dfPFA_bar_odds_ratio_pfa['selfDefinedEthnicityGroup'], labels=dfPFA_bar_odds_ratio_pfa['lab']))
   labels = LabelSet(x='ethnicity', y='ratios', text='labels',text_color = "white",
                     y_offset=10, x_offset =-11.5, text_font_size = '14px', source=source)
   bk_plotOut.add_layout(labels)
   bk_plotOut.add_layout(Title(text="Odds of a person being stop and searched relative to a person\nof white ethnicity in "+str(pfaName_ops)+", "+str(year_ops[0])+"-"+str(year_ops[1]), text_font_size="12pt", text_font_style="bold"), 'above')
   bk_plotOut.toolbar.autohide = True
   return bk_plotOut














#@pn.depends(year_ops,pfaName_ops, legislation_ops)
#def plot_bar_odds_ratio(year_ops,pfaName_ops, legislation_ops):
#   dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
#   dfPFA_bar_odds_ratio = dfPFA_ops.groupby(
#      ['pfaName', 'legislation', 'selfDefinedEthnicityGroup'],as_index=False)[
#          ['numberOfSearches','population']].agg({'numberOfSearches':'sum','population':'sum'})
#   #print(dfPFA_bar_odds_ratio)
#   dfPFA_bar_odds_ratio['rateOfSearches'] = ((
#      dfPFA_bar_odds_ratio['numberOfSearches'] / dfPFA_bar_odds_ratio['population'])*100)
#   dfPFA_bar_odds_ratio = dfPFA_bar_odds_ratio.loc[[5,0,1,2,3,4]]
#   dfPFA_bar_odds_ratio['ratios'] = [round(i/dfPFA_bar_odds_ratio['rateOfSearches'][0], 2) for i in dfPFA_bar_odds_ratio['rateOfSearches']]
#   dfPFA_bar_odds_ratio.replace([np.inf, -np.inf], np.nan, inplace=True)
#   hv_plotOut = dfPFA_bar_odds_ratio.hvplot.bar(
#      x='selfDefinedEthnicityGroup',y='ratios',
#      color=hv.Cycle(['#E10000','#130C16','#130C16','#130C16','#130C16','#130C16']),
#     xlim=[0,None], legend = False, stacked=False, height=250, width = 490).opts(hooks=[lambda p, _: p.state.update(border_fill_alpha=1)])
#   bk_plotOut =  hv.render(hv_plotOut)
#   bk_plotOut.add_layout(Title(text="Odds Ratio: Ethnic disparties in\n" + str(pfaName_ops), text_font_size="12pt", text_font_style="bold"), 'above')
#   bk_plotOut.toolbar.autohide = True
#   return bk_plotOut


#@pn.depends(year_ops,pfaName_ops,legislation_ops)
# def plot_bar_odds_ratio_UK_abs(year_ops, pfaName_ops, legislation_ops):
#    dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
#    dfPFA_bar_odds_ratio_UK_abs = dfPFA_ops.groupby(
#      ['legislation', 'selfDefinedEthnicityGroup'],as_index=False)[
#         ['numberOfSearches','population']].agg({'numberOfSearches':'sum','population':'sum'})
#   dfPFA_bar_odds_ratio_UK_abs = dfPFA_bar_odds_ratio_UK_abs.loc[[5,0,1,2,3,4]]
#   dfPFA_bar_odds_ratio_UK_abs['ratios'] = [round(i/dfPFA_bar_odds_ratio_UK_abs['numberOfSearches'][0], 2) for i in dfPFA_bar_odds_ratio_UK_abs['numberOfSearches']]
#   dfPFA_bar_odds_ratio_UK_abs.replace([np.inf, -np.inf], np.nan, inplace=True)
#   hv_plotOut = dfPFA_bar_odds_ratio_UK_abs.hvplot.bar(
#      x='selfDefinedEthnicityGroup',y='ratios',
#      color=hv.Cycle(['#E10000','#130C16','#130C16','#130C16','#130C16','#130C16']),
#      xlim=[0,None], legend = False, stacked=False, height=250, width = 490).opts(hooks=[lambda p, _: p.state.update(border_fill_alpha=1)])
#   bk_plotOut =  hv.render(hv_plotOut)
#   bk_plotOut.add_layout(Title(text="Absolute: Ethnic disparties in the UK", text_font_size="12pt", text_font_style="bold"), 'above')
#   bk_plotOut.toolbar.autohide = True
#   return bk_plotOut

#@pn.depends(year_ops,pfaName_ops, legislation_ops)
#def plot_bar_odds_ratio_abs(year_ops,pfaName_ops, legislation_ops):
#   dfPFA_ops = create_options_dfPFA(dfPFA, year_ops,pfaName_ops, legislation_ops)
#   dfPFA_bar_odds_ratio_abs = dfPFA_ops.groupby(
#      ['pfaName', 'legislation', 'selfDefinedEthnicityGroup'],as_index=False)[
#          ['numberOfSearches','population']].agg({'numberOfSearches':'sum','population':'sum'})
#   dfPFA_bar_odds_ratio_abs = dfPFA_bar_odds_ratio_abs.loc[[5,0,1,2,3,4]]
#   dfPFA_bar_odds_ratio_abs['ratios'] = [round(i/dfPFA_bar_odds_ratio_abs['numberOfSearches'][0], 2) for i in dfPFA_bar_odds_ratio_abs['numberOfSearches']]
#   dfPFA_bar_odds_ratio_abs.replace([np.inf, -np.inf], np.nan, inplace=True)
#   hv_plotOut = dfPFA_bar_odds_ratio_abs.hvplot.bar(
#      x='selfDefinedEthnicityGroup',y='ratios',
#      color=hv.Cycle(['#E10000','#130C16','#130C16','#130C16','#130C16','#130C16']),
#      xlim=[0,None], legend = False, stacked=False, height=250, width = 490).opts(hooks=[lambda p, _: p.state.update(border_fill_alpha=1)])
#   bk_plotOut =  hv.render(hv_plotOut)
#   bk_plotOut.add_layout(Title(text="Absolute: Ethnic disparties in\n" + str(pfaName_ops), text_font_size="12pt", text_font_style="bold"), 'above')
#   bk_plotOut.toolbar.autohide = True
#   return bk_plotOut
      
#dfPFA_years = dfPFA[dfPFA['year'].between(2012,2013, inclusive='both')]
#dfPFA_years_ssNum = dfPFA_years.groupby(
 #  ['pfaName','year'])['numberOfSearches'].sum().reset_index(name="numberOfSearches")
#dfPFA_years_ssNum_area = dfPFA_years_ssNum[dfPFA_years_ssNum['pfaName'] == 'Avon and Somerset']
# Plotting initial graph
#df.sort_values(by=["pfaName"]) 
#df = df.groupby(['pfaName','year'], as_index=False).agg({'numberOfSearches':'sum'})
#chart = df.hvplot.line(x='year',y='numberOfSearches')

#==============================================================================
#                             3. Compile                           #                                
#==============================================================================
pn.extension()
#title = "# Stop and Search Statistics"
#logo = pn.panel(r'C:\Users\MatthewTibbles\Downloads\stopwatch_logo.png', width=250, align='start')
logo = pn.panel(r'stopwatch_logo.png', width=250, align='start')

def get_map(lat=53.3555, long=0.0104, zoom_start=5.5):
    return fm.Map(location=[lat,long], zoom_start=zoom_start)

def marker():
    fm.Marker([53.3555,0.0104], popup='location', tooltip='click for more', ).add_to(map)
    fm.TileLayer('cartodbdark_matter').add_to(map)
map = get_map()
marker()
pfaShape = gpd.read_file('pfaShape.geojson')
#pfaShape = gpd.read_file(r'C:\Users\MatthewTibbles\Downloads\pfaShape.geojson')
pfaShape = pfaShape[pfaShape.pfaName != 'Northern Ireland']
pfaShape = pfaShape.reset_index(drop=True)
pfaShape = pfaShape.sort_values(by=['pfaName']) 
pfaShapeData = dfPFA[dfPFA.pfaName != 'British Transport Police']
pfaShapeData = pfaShapeData.groupby(['pfaName'],as_index=False).agg({'numberOfSearches':'sum'})


pfaShape['numberOfSearches'] = pfaShapeData['numberOfSearches']



def get_map(lat=53.3555, long=0.0104, zoom_start=5.5):
    return fm.Map(location=[lat,long], zoom_start=zoom_start, tiles=None)

def marker():
    fm.Marker([53.3555,0.0104], popup='location', tooltip='click for more').add_to(map)

map = get_map()
fm.TileLayer('cartodbdark_matter' ,name="Light Map",control=False).add_to(map)

import folium.plugins
import branca
import branca.colormap as cm
bins = list(pfaShape["numberOfSearches"].quantile([0, 0.25, 0.5, 0.90, 0.99, 1]))


#color_map=cm.linear.YlOrRd_09.scale(1,100)
#color_map=color_map.to_step(index=bins)
#color_map=color_map.to_linear()
#color_map.add_to(map)


bins = list(pfaShape["numberOfSearches"].quantile([0, 0.25, 0.5, 0.90, 0.99, 1]))

cp = fm.Choropleth(
    geo_data=pfaShape,
    name="choropleth",
    data=pfaShape,
    columns=["pfaName", "numberOfSearches"],
    key_on="feature.properties.pfaName",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=.1,
    bins=bins,
    legend_name="Total Stop & Search number",
).add_to(map)


fm.LayerControl().add_to(map)

style_function = lambda x: {'fillColor': '#ffffff', 
                            'color':'#000000', 
                            'fillOpacity': 0.1, 
                            'weight': 0.1}
highlight_function = lambda x: {'fillColor': '#000000', 
                                'color':'#000000', 
                                'fillOpacity': 0.50, 
                                'weight': 0.1}

toolTip = fm.features.GeoJson(
    pfaShape,
    style_function=style_function, 
    control=False,
    highlight_function=highlight_function, 
    tooltip=fm.features.GeoJsonTooltip(
        fields=['pfaName','numberOfSearches'],
        aliases=['Police Force Area: ','Numbr of Searches: '],
        style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;") 
    )
)

map.add_child(toolTip)
map.keep_in_front(toolTip)
fm.LayerControl().add_to(map)

mapItem = pn.panel(map, height=600, width=600)






mapItem = pn.panel(map, height=585, width = 690)














plots_box = pn.WidgetBox(pn.Column(
   pn.Row(plot_tsline),pn.Row(mapItem ), pn.Row(plot_tsline, plot_bar_eth_prop, align="start", width=600,sizing_mode="stretch_width")))
plots_box = pn.WidgetBox(pn.Column(
   pn.Row(plot_tsline),pn.Row(mapItem ), pn.Row(plot_tsline, plot_bar_eth_prop, align="start", width=600,sizing_mode="stretch_width")))



#css = '''
#.bk.panel-widget-box {
#  background: #F6F6F6;
#  border-radius: 5px;
#  border: 2px #E9E9E9 solid;
#}
#'''
#E9e9e9
#pn.extension(raw_css=[css])
import base64
def image_to_data_url(filename):
    ext = filename.split('.')[-1]
    prefix = f'data:image/{ext};base64,'
    with open(filename, 'rb') as f:
        img = f.read()
    return prefix + base64.b64encode(img).decode('utf-8')
#logo2 = image_to_data_url('C:\\Users\\MatthewTibbles\\Downloads\\stopwatch_logo.png')
logo2 = image_to_data_url('stopwatch_logo.png')
one = pn.widgets.Button(name='Overview', width=50, button_type='primary', height = 35)
two = pn.widgets.Button(name='Ethnic Disparities', width=50, button_type='primary', height = 35)
toggle_group = pn.widgets.ToggleGroup(name='ToggleGroup', options=['Overview', 'Ethnic Disparities'], 
                                      behavior="radio", height = 35)
#, favicon = logo2
from panel.template import DarkTheme
template = pn.template.FastGridTemplate(theme =  "dark",
    site="", title="Interactive Stop and Search Tracker",
    sidebar=[logo, toggle_group, year_ops, pfaName_ops, legislation_ops, summary_text],
    sidebar_width = 380, logo = logo2, header_background = '#130C16', header_accent_base_color = '#130C16',
    header_neutral_color = '#130C16', accent_base_color = '#130C16', corner_radius = 5, shadow = False, 
    prevent_collision = True, toggle = True
)
main = pn.Row(
   pn.Column(
      pn.Row(plot_tsline),
      pn.Row(mapItem),
      pn.Row(plot_bar_odds_ratio_UK)
      ),
      pn.Column(
         pn.Row(plot_bar_eth_prop),
         pn.Row(plot_tsscatter),
         pn.Row(plot_bar_odds_ratio_pfa)
      )
   ) 

template.main[:2, :7]= plot_tsline
template.main[:2, 7:12]=plot_bar_eth_prop
template.main[2:6, :7]=mapItem
template.main[2:6, 7:12]=plot_tsscatter
template.main[6:8, :7]=plot_bar_odds_ratio_UK 
template.main[6:8, 7:12]=plot_bar_odds_ratio_pfa

#pn.Column(
 #  pn.Row(plot_tsline),
 #  pn.Row(mapItem)
 #  )
#tabs = pn.Tabs((template, template)
#tabs.show()
template.show()


#from panel.template import DarkTheme
#dark_material = pn.template.FastGridTemplate(title='Material Template', background_color = "pink")
#dark_material.sidebar.append(logo)
#dark_material.sidebar.append(pfaName_ops)
#dark_material.sidebar.append(legislation_ops)
#dark_material.sidebar.append(summary_text)

#main = pn.Row(
#   pn.Column(
#      pn.WidgetBox(pn.Row(plot_tsline)),
#      pn.WidgetBox(pn.Row(mapItem))
#      ),
#      pn.Column(pn.WidgetBox(
#         pn.Row(plot_bar_eth_prop)),
#         pn.Row(pn.WidgetBox(plot_tsscatter))
 #     )
#   )  
#dark_material.main.append(main)

#dark_material.show()

#bootstrap = pn.template.FastListTemplate(title=pn.panel(r'C:\Users\MatthewTibbles\Downloads\stopwatch_logo.png', width=250, align='start'))
#bootstrap.sidebar.append(header_box)

#bootstrap.main.append(main)

#bootstrap.show()

# DO NOT DELETE
# https://panel.holoviz.org/gallery/links/bokeh_property_editor.html
#https://stackoverflow.com/questions/55542537/how-do-i-set-bokeh-tick-and-font-options-in-holoviews
                  