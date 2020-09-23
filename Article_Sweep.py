"""
Jayce Slesar
6/9/2020
Functions and a Class to collect, clean, and organize a datapull from rxiv
"""

import json
import re
import requests
from difflib import SequenceMatcher
import pandas as pd
import urllib3
from pathlib import Path
import pathlib
from datetime import date
import datetime
import lxml.html



# keeps track of articles flagged as not useful (may not use yet)
def flag_clean(df):
        new_bad_DOI = []
        rows_to_drop = []
        for index, row in df.iterrows():
            if not pd.isna(row["flag"]):
                rows_to_drop.append(index)
                new_bad_DOI.append(row["DOI"])
        return (df.drop(df.index[rows_to_drop]), new_bad_DOI)


# cleans some pandas stuff that happens because I dont use a real index
def pd_clean(df):
    for col in df.columns:
        if "Unnamed" in col:
            df = df.drop(col, 1)
    if "" in df.columns:
        return df.drop("", 1)
    else:
        return df


# lowerize my words in list for comparisons
def lowerize(words:list) -> list:
    lowered = [w.lower() for w in words]
    return lowered


# used to tell how similar to strings are
def similar(a:str, b:str) -> float:
    return SequenceMatcher(None, a, b).ratio()


# searches the title words and keywords list provided to ween out titles
# TODO:does need improvement
def find_relevant_titles(title:str, good_keywords:list, bad_keywords:list) -> bool:
    title = title.lower()
    title_split = title.split()
    good_keywords = lowerize(good_keywords)
    bad_keywords = lowerize(bad_keywords)
    title_split = lowerize(title_split)
    for w in bad_keywords:
        if w in title or w in title_split:
            return False
    for w in good_keywords:
        if w in title or w in title_split:
            return True
    return True


# class to organize data and run everything
class Article_Sweep:
    # initializer
    def __init__(self, good_keywords:list, bad_keywords:list, auto_params:list, manual_params:list) -> None:
        # list of names of databses I currently pull from (just preprints right now)
        self.DATABASES = ["rxiv"]
        # pathing to work on any machine
        rxiv_path = Path(Path.cwd() / "rxiv.csv")
        # clean it (returns a tuple of things I need)
        newrxiv = flag_clean(pd.read_csv(rxiv_path))
        self.rxiv = newrxiv[0]  # this is the actual df
        bad_DOI_path = Path(Path.cwd() / "bad_DOI.csv")
        self.bad_DOI = pd.read_csv(bad_DOI_path)
        self.new_bad_DOI = newrxiv[1]  # this is the new flagged DOI's as bad
        all_bad_DOI = self.new_bad_DOI + self.bad_DOI["DOI"].to_list()  # all the bad DOI's in history
        all_bad_DOI = list(set(all_bad_DOI))  # remove dupes
        self.bad_DOI["DOI"] = pd.Series(all_bad_DOI)
        self.bad_DOI = pd_clean(self.bad_DOI)  # clean
        self.bad_DOI.to_csv("bad_DOI.csv")  # save
        self.JSON_PAPERS = 'https://connect.medrxiv.org/relate/collection_json.php?grp=181'
        self.pubmed = None # TODO::this
        # others -> (?):
        self.GOOD_KEYWORDS = good_keywords
        self.BAD_KEYWORDS = bad_keywords
        
        
        # parses the rxiv pre-release database
        def get_rxiv(self):
            to_add = []
            database_names = None
            try:
                database_names = self.rxiv["title"].to_list()
            # first run of database, no records collected yet
            except KeyError:
                database_names = []
                pass
            self.words = ""  # used to track most common words across titles
            # flag as known preprints
            # pings and gets the json object of daily info
            data = requests.get(self.JSON_PAPERS).json()
            # search each title
            for paper_data in data["rels"]:
                curr_title = paper_data["rel_title"]
                if paper_data["rel_doi"] in self.bad_DOI["DOI"].to_list():
                    continue
                if curr_title not in database_names:
                    curr_match = {}
                    # run the relevant function (function returns True or False)
                    if find_relevant_titles(curr_title, self.GOOD_KEYWORDS, self.BAD_KEYWORDS):
                        try:
                            self.words += curr_title + ' '  # used to track most common words across titles
                            print(paper_data)  # print it to make sure it is UTF-8 (romance language)
                            # pull the auto stats
                            curr_match["title"] = curr_title
                            curr_match["DOI"] = paper_data["rel_doi"]
                            curr_match["abstract"] = paper_data["rel_abs"]
                            curr_match["pre_print_release_date"] = paper_data["rel_date"]
                            curr_match["publisher"] = paper_data["rel_site"]
                            insts = []
                            for author in paper_data["rel_authors"]:
                                if author["author_inst"] not in insts:
                                    insts.append(author["author_inst"])
                            curr_match["authored_by"] = insts
                            # build the param list
                            for param in self.params:
                                curr_match[param] = ""
                            curr_match["database"] = self.DATABASES[0]
                            # flag to delete data on run if it turns out to be a bad article
                            curr_match["flag"] = ""
                            to_add.append(curr_match)
                        except:
                            continue
            new_rxiv_preprints = pd.DataFrame(to_add)
            all_rxiv = pd_clean(pd.concat([self.rxiv, new_rxiv_preprints]))
            all_rxiv.to_csv("rxiv.csv")


        # actualy run
        get_rxiv(self)
