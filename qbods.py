import pandas as pd
import re
import statistics
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import textwrap

##################
# General functions
##################

#Use regex to convert a single string from camel to snake case
def camel_to_snake(name):
    name = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name) #note that this uses a dash instead of an underscore
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', name).lower()

#read in a BODS codelist csv and pull out the codelist column as a list
def read_codelist(url,case = 'camel'):
  df = pd.read_csv(url)
  if case == 'snake': #can return in snake case with required
    return(df['code'].apply(camel_to_snake).tolist())
  else:
    if case == 'camel':
      return(df['code'].tolist())


##################
# Queries
##################

def q111(ooci,ooc):
    #merge ooci table with ooc table to get missing values
        df = pd.merge(ooc['_link'],
                ooci[['_link_ooc_statement','type','beneficialOwnershipOrControl']],
                how = 'left',
                left_on = '_link',
                right_on = '_link_ooc_statement')

    #Generate table with crosstab
        out = df['beneficialOwnershipOrControl'].fillna('Missing').value_counts().to_frame()
        ax = out.plot.barh(stacked = True)
        ax.set(ylabel = None,xlabel = "Number of OOC statements")
        fig = ax.get_figure()
        plt.close()
        return([out,fig])

def q121(ooc,oops,ooes):
    #Merge OOC and person statement tables by interested party
    df = pd.merge(ooc.dropna(subset=['interestedParty_describedByPersonStatement'])['interestedParty_describedByPersonStatement'],
    oops[['statementID', 'personType']],
    left_on = "interestedParty_describedByPersonStatement",
    right_on= "statementID",
     how = "left")

    #Count person types of person owners
    df = df['personType'].value_counts().to_frame().rename(columns = {'personType': 'ownerType'})

    #Merge OOC and entity statement tables by interested party
    df1 = pd.merge(ooc.dropna(subset=['interestedParty_describedByEntityStatement'])["interestedParty_describedByEntityStatement"],
                ooes[['statementID', 'entityType']],
                left_on = "interestedParty_describedByEntityStatement",
                right_on= "statementID",
                how = "left")

    #Count entity types of entity owners
    df1 = df1['entityType'].value_counts().to_frame().rename(columns = {'entityType': 'ownerType'})

    #Add person and entity owner counts together
    out = df.append(df1)

    #Read in all person and entity types from codelist and append
    ptypes = read_codelist('https://raw.githubusercontent.com/openownership/data-standard/0.2.0/schema/codelists/personType.csv',
    case = 'camel')
    etypes = read_codelist('https://raw.githubusercontent.com/openownership/data-standard/0.2.0/schema/codelists/entityType.csv',
    case = 'camel')
    alltypes = ptypes+etypes


    #Add missing codelists and fill with zero
    out = out.reindex(index = alltypes,fill_value = 0)

    #Add totals row
    out = out.append(pd.DataFrame(sum(out['ownerType']),
                                columns = ['ownerType'],
                                index = ['All']))

    #Sort
    out = out.sort_values(by = ['ownerType'],ascending = False)

    #Barplot
    ax = out.plot.barh(legend = False)
    ax.set(ylabel = None,xlabel = "Number of OOC statements")
    fig = ax.get_figure()
    plt.close()
    return([out,fig])

def q122(ooci,ooc,es):
    #Merge interests where BO == True with ooc statements and filter for ownership by entities
    df = pd.merge(ooci[ooci['beneficialOwnershipOrControl'] == True]['_link_ooc_statement'],
    ooc[['_link','subject_describedByEntityStatement','interestedParty_describedByEntityStatement']],
    how = 'left',
    left_on = '_link_ooc_statement',
    right_on = '_link')

    df = df.loc[df['interestedParty_describedByEntityStatement'].notnull()]

    #Only do the rest if there are entities with BO
    if len(df) > 0:
        df = pd.merge(df,
        ooes[['statementID','incorporatedInJurisdiction_name']],
        how = 'left',
        left_on='subject_describedByEntityStatement',
        right_on = 'statementID')
        df = df.drop_duplicates(subset = ['statementID'])
        out = df['incorporatedInJurisdiction_name'].fillna('Missing').value_counts().to_frame()
        #Add totals row
        out = out.append(pd.DataFrame(sum(out['incorporatedInJurisdiction_name']),
                                    columns = ['incorporatedInJurisdiction_name'],
                                    index = ['All']))
        #Plot
        ax = out.drop(labels = ['All']).head(10).plot.barh()
        ax.set(ylabel = None,xlabel = "Number of OOC statements")
        fig = ax.get_figure()
        plt.close()
        return([out,fig])
    else:
        print('No entities with other entities as beneficial owners')
        return(['No table returned','No plot returned'])

def q131(ooci,ooc):
    #merge ooci table with ooc table to get missing values
    df = pd.merge(ooc['_link'],
            ooci[['_link_ooc_statement','type','beneficialOwnershipOrControl']],
            how = 'left',
            left_on = '_link',
            right_on = '_link_ooc_statement')

    #Generate table with crosstab
    out = pd.crosstab(df['type'].fillna('Missing'),df['beneficialOwnershipOrControl'].fillna('Missing'),margins = True)

    #Add in missing codelist entries and replace with zeros
    rights = read_codelist('https://raw.githubusercontent.com/openownership/data-standard/0.2.0/schema/codelists/interestType.csv')
    out = out.reindex(index = rights+['Missing','All'],fill_value = 0)

    #Sort
    out = out.sort_values(by = ['All'],ascending = False)

    # Graph
    ax = out.drop(labels = ['All']).drop(columns = ['All']).plot.barh(stacked = True)
    ax.set(ylabel = None,xlabel = "Number of OOC statements")
    fig = ax.get_figure()
    plt.close()

    return([out,fig])

def q132(ooci,ooc):
    # Generate output table with crosstab
    df = pd.merge(ooc['_link'],
        ooci[['_link_ooc_statement','interestLevel','beneficialOwnershipOrControl']],
        how = 'left',
        left_on = '_link',
        right_on = '_link_ooc_statement')

    out = pd.crosstab(df['interestLevel'].fillna('Missing'),df['beneficialOwnershipOrControl'].fillna('Missing'),margins = True)

    levels = read_codelist('https://raw.githubusercontent.com/openownership/data-standard/0.2.0/schema/codelists/interestLevel.csv')
    out = out.reindex(index = levels+['Missing','All'],fill_value = 0)
    out = out.sort_values(by = 'All',ascending = False)


    #Plot
    ax = out.drop(labels = ['All']).drop(columns = ['All']).plot.barh(stacked = True)
    ax.set(ylabel = None,xlabel = "Number of OOC statements")
    fig = ax.get_figure()
    plt.close()
    return([out,fig])

def q141(ooci):
    ### Output table ------------------

    shares = ['share_exact','share_minimum','share_maximum']
    df = ooci.reindex(columns = shares,fill_value = None)
    out = df.notna().sum().to_frame(name = 'Number non-missing values')

    ### Graph -------------------------

    ax = out.plot.barh(legend = False)
    ax.set(ylabel = None,xlabel = 'Number of non-missing values')
    fig = ax.get_figure()
    plt.close()
    return([out,fig])

def q142(ooci,threshold):
    ### Prepare output table -----------------------
    shares = ['share_exact','share_minimum','share_maximum']
    df = ooci.reindex(columns = shares,fill_value = None)
    df['max-min share'] = df['share_maximum'] - df['share_minimum']
    ### Final output table -------------------------
    idx = ['Most common value','Number of unique values','Minimum share','Maximum share']
    out = df.mode().append(df.nunique(),ignore_index = True).append(df.min(),ignore_index = True).append(df.max(),ignore_index = True)
    out.index = idx

    finalout = [out]
    ### Graph --------------------------------------
    if out['share_exact']['Number of unique values'] > 0:
        ax = df['share_exact'].hist()
        ax.set(xlabel = 'Exact share (%)',ylabel = 'Number of entries')
        ax.axvline(threshold)
        fig1 = ax.get_figure()
        plt.close()
        finalout.append(fig1)

    if out['share_minimum']['Number of unique values'] > 0:
        ax1 = df['share_minimum'].hist()
        ax1.set(xlabel = 'Minimum share (%)',ylabel = 'Number of entries')
        ax1.axvline(threshold)
        fig2 = ax1.get_figure()
        plt.close()
        finalout.append(fig2)

    if out['share_maximum']['Number of unique values'] > 0:
        ax2 = df['share_maximum'].hist()
        ax2.set(xlabel = 'Maximum share (%)',ylabel = 'Number of entries')
        ax2.axvline(threshold)
        fig3 = ax2.get_figure()
        plt.close()
        finalout.append(fig3)
    
    return(finalout)

def q211(ooes):
    d = {'Name': [sum(ooes['name'].notna()),sum(ooes['name'].isna())]}
    out = pd.DataFrame(d,index = ['Present','Missing'])
    out
    ax = out.plot.barh(legend = False)
    ax.set(xlabel = None,ylabel = 'Number of entries')
    fig = ax.get_figure()
    plt.close()
    return([out,fig])