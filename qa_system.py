'''
author: Anand Raman

Question answering system that uses 2013,2014
Business Insider articles to answer the following questions
    1. Which companies went bankrupt in month X of year Y?
        Returns: list of companies and the context from which it was pulled
    2. What affects GDP?
        returns: list of factors affecting GDP. i.e. Unemployment
        and the sentence from which this factor was pulled
        a. After returning factors that affect GDP,
        The user is prompted to ask a follow-up question.
        If no follow-up, user is allowed to ask other questions (i.e. 1 and 3)
    3. Who is the CEO of company X.
'''

import pandas as pd
from elasticsearch import Elasticsearch
from os import listdir
import string
import spacy
from string import punctuation

# dictionary of months for company question
month_dict = {'January': '01',
              'February': '02',
              'March': '03',
              'April': '04',
              'May': '05',
              'June': '06',
              'July': '07',
              'August': '08',
              'September': '09',
              'October': '10',
              'November': '11',
              'December': '12'}

# FUNCTION DEFINITIONS


def question_type(question):
    tokens = question.split(" ")
    if tokens[0] == "Who":
        return "CEO"
    elif tokens[0] == "What":
        return "GDP"
    elif tokens[0] == "Which":
        return "COMPANY"
    elif tokens[0] == "No":
        return "No further questions"
    else:
        print('Unrecognized question type. Question must \
            begin with "Who", "What", or "Which"')


def gdp_extraction(doc):
    # takes a doc
    # returns a passage of 3 sentences
    # sentence before sent containing GDP and one after
    gdp_psg = []
    doc_sents = [sent for sent in doc.sents]
    for i in range(len(doc_sents)):
        try:
            if "GDP" in doc_sents[i].text:
                psg = doc_sents[i-1].text + " " + doc_sents[i].text + \
                    " " + doc_sents[i+1].text
                gdp_psg.append(psg)
        except IndexError:
            gdp_psg.append(doc_sents[i].text)
    return gdp_psg


# QA SYSTEM
nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser"])
sentencizer = nlp.create_pipe("sentencizer")
nlp.add_pipe(sentencizer)

es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

files = listdir('data/articles/')
files = [file for file in files if file != ".DS_Store"]
text_dat = []
for num, file in enumerate(files):
    fname = 'data/articles/' + file
    f = open(fname, encoding='utf8', errors='replace')
    month_yr = file[0:7]
    article = f.read()
    # removing nonsense chars
    printable = set(string.printable)
    article = ''.join(filter(lambda x: x in printable, article))
    # creating dictionary for input into elasticsearch db
    article_dict = {'date': month_yr,
                    'content': article}
    article_db = es.index(index='businessinsider', doc_type='article',
                          id=num, body=article_dict)
f.close()

for i, val in enumerate(text_dat):
    article_db = es.index(index='businessinsider',
                          doc_type='article', id=i, body=val)

question = input("Ask a question: ")

while(question not in ["No further questions", "No further questions."]):

    q_type = question_type(question)
    if question_type(question) not in ["GDP", "CEO", "COMPANY"]:
        question = input("Please ask another question: ")

    question_processed = nlp(question)
    if q_type == "CEO":
        # processing question
        company_lst = [ent.text for ent in question_processed.ents]
        if len(company_lst) > 1:
            print("Question contains more than one entity.")
            print("Combining entities for query")
            company = ""
            for i in range(len(company_lst)):
                company += company_lst[i]
        else:
            company = company_lst[0]

        search_term = company + " CEO"
        query = {'match': {'content': search_term}}

    elif q_type == "COMPANY":
        date = [ent.text for ent in question_processed.ents]
        date = date[0]
        date_tokens = date.split(' ')
        month_txt = date_tokens[0]
        month_num = month_dict[month_txt]
        year = date_tokens[2]
        date_searchable = year + "-" + month_num
        search_term = "bankrupt bankruptcy"
        query = {'bool': {'must': {'match': {'content': search_term}},
                          'filter': {'term': {'date': date_searchable}}}}

    elif q_type == "GDP":
        search_term = "contribution breakdown GDP"
        query = {'match': {'content': "GDP"}}

    doc_search = es.search(index='businessinsider', doc_type='article', body={
                                 'query': query})

    if q_type != "GDP":
        # selecting the top article
        top_doc = doc_search['hits']['hits'][0]['_source']['content']
        # processing top article with spacy
        top_doc_spacy = nlp(top_doc)
        # breaking into sentences
        top_sents = [{'sent': str(sent)} for sent in top_doc_spacy.sents]
    elif q_type == "GDP":
        top_docs = doc_search['hits']['hits']
        hit_lst = []
        for hit in top_docs:
            lst_itm = nlp(hit['_source']['content'])
            hit_lst.append(lst_itm)
        top_sents = []
        for doc in hit_lst:
            gdp_psgs = gdp_extraction(doc)
            top_sents.extend(gdp_psgs)
        top_sents = [{'sent': sent} for sent in top_sents]

    # creating a sentence index
    for i, sent in enumerate(top_sents):
        sent_db = es.index(index='sentences', doc_type='sent', id=i, body=sent)

    # use search_term here because query contains
    # filter in the "COMPANY" case.
    result = es.search(index='sentences', doc_type='sent',
                       body={'size': 10,
                             'query': {'match':
                                       {'sent': search_term}}})

    if q_type == "CEO":
        # selecting the top sentence
        answer_sent = result['hits']['hits'][0]['_source']['sent']
        # processing sentence
        answer_processed = nlp(answer_sent)
        answer = [ent.text for ent in answer_processed.ents
                  if ent.label_ == "PERSON"]
        # now delete index
        es.indices.delete(index='sentences', ignore=[400, 404])
        print(answer)

    elif q_type == "COMPANY":
        answer_sents = []
        for hit in result['hits']['hits']:
            # appending processed sentences
            answer_sents.append(nlp(hit['_source']['sent']))

        answer = []
        for sent in answer_sents:
            companies = [ent.text for ent in sent.ents if ent.label_ == "ORG"]
            answer.extend(companies)

        answer = [ans for ans in answer if ans not in ['Reuters', 'Icahn',
                                                       'Apple', 'Bloomberg']]

        print(answer)
        # now delete index
        es.indices.delete(index='sentences', ignore=[400, 404])

    elif q_type == "GDP":
        answer = []
        for hit in result['hits']['hits']:
            answer.append(hit['_source']['sent'])
        for text in answer:
            print(text)
        follow_up = input("Would you like to ask a GDP followup: ")
        if follow_up == "Yes" or follow_up == "yes":
            print("You may ask a follow up of the following format")
            print("What percentage of drop or increase is associated with X?")
            garbage = "What percentage of drop or increase is associated with"
            factor = input("Ask your followup: ")
            while factor != "No further followups.":
                factor_tks = factor.split(' ')
                factor_tks = [tk for tk in factor_tks if tk not in garbage]
                keyword = ' '.join(factor_tks)
                keyword_np = ''.join(
                    [c for c in keyword if c not in punctuation])
                search_term = keyword_np + " GDP"
                result = es.search(index='sentences', doc_type='sent',
                                   body={'size': 300,
                                         'query': {'match':
                                                   {'sent': search_term}}})
                answer_sents = []
                for hit in result['hits']['hits']:
                    answer_sents.append(nlp(hit['_source']['sent']))

                answer = []
                for sents in answer_sents:
                    labels = [ent.label_ for ent in sents.ents]
                    if "PERCENT" in labels:
                        answer.append(sents.text)

                for i, text in enumerate(answer):
                    if i < 4:
                        print(text)
                print("If you are done asking followups, enter \
'No further followups.'")
                factor = input("Ask another followup: ")
        es.indices.delete('sentences', ignore=[400, 404])

    question = input("Ask another question: ")
