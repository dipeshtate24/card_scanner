import pandas as pd
import cv2
import pytesseract
import spacy
import re
import string
import warnings
from io import StringIO 
warnings.filterwarnings('ignore')


# Load NER model
model_ner = spacy.load("output/model-best/")


def clean_text(txt):
    whitespace = string.whitespace
    punctuation = '!#$%&\'()*+:;<=>?[\\]^`{|}~'
    tableWhiteSpace = str.maketrans("", "", whitespace)
    tablePunctuation = str.maketrans("", "", punctuation)
    text = str(txt)
    text = text.lower()
    removewhitespace = text.translate(tableWhiteSpace)
    removepunctuation = removewhitespace.translate(tablePunctuation)

    return str(removepunctuation)


def parser(text, label):
    if label == "PHONE":
        text = text.lower()
        text = re.sub(r"\D", "", text)

    elif label == "EMAIL":
        text = text.lower()
        allow_special_char = "@_.\-"
        text = re.sub(r"[^A-Za-z0-9{} ]".format(allow_special_char), "", text)

    elif label == "WEB":
        text = text.lower()
        allow_special_char = ":/.%#\-"
        text = re.sub(r"[^A-Za-z0-9{} ]".format(allow_special_char), "", text)

    elif label in ("I-NAME"):
        text = text.lower()
        allow_special_char = ":/.%#-"
        text = re.sub(r"[^a-z ]", "", text)
        text = text.title()

    elif label in ("B-NAME"):
        text = text.lower()
        allow_special_char = ":/.%#-"
        text = re.sub(r"[^a-z ]", "", text)
        text = text.title()

    elif label in ("DES"):
        text = text.lower()
        allow_special_char = ":/.%#-"
        text = re.sub(r"[^a-z ]", "", text)
        text = text.title()

    elif label == "ORG":
        text = text.lower()
        allow_special_char = ":/.%#-"
        text = re.sub(r"[^a-z0-9 ]", "", text)
        text = text.title()

    return text


def getpredictions(image):
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    text_data = pytesseract.image_to_data(gray)
    
    data = StringIO(text_data)
    
    df = pd.read_csv(data, sep='\t')
    
    df.dropna(inplace=True)
    
    df["text"] = df["text"].apply(clean_text)
    
    # convert Data into content
    df_clean = df.query("text != ''")
    content = " ".join([w for w in df_clean["text"]])
    
    doc = model_ner(content)
    # spacy.displacy.serve(doc, style="ent")
    
    docjson = doc.to_json()
    
    doc_text = docjson["text"]
    
    dataframe_tokens = pd.DataFrame(docjson["tokens"])
    
    dataframe_tokens["token"] = dataframe_tokens[["start", "end"]].apply(lambda x: doc_text[x[0]:x[1]],axis=1)

    pd.DataFrame(docjson["ents"])


    pd.DataFrame(docjson["ents"])[["start", "label"]]

    doc_ents = pd.DataFrame(docjson["ents"])[["start", "label"]]

    dataframe_tokens = pd.merge(dataframe_tokens, doc_ents, how="left", on="start")

    dataframe_tokens.fillna('O', inplace = True)

    df_clean['conf'] = df_clean['conf'].astype(int)

    #join label to df_clean dataframe
    df_clean['text'].apply(lambda x: len(x)+1)
    
    # join label to df_clean dataframe
    df_clean["text"].apply(lambda x: len(x)+1).cumsum() - 1

    df_clean["end"] = df_clean["text"].apply(lambda x: len(x)+1).cumsum() - 1

    df_clean["start"] = df_clean[["text", "end"]].apply(lambda x: x[1] - len(x[0]), axis=1)

    # to get correct start position
    df_clean[["text", "end"]].apply(lambda x: x[1] - len(x[0]), axis=1)
    
    # inner join with start 
    dataframe_info = pd.merge(df_clean, dataframe_tokens[["start", "token", "label"]], how="inner", on="start") 
    
    info_array = dataframe_info[["token", "label"]].values
    entities = {"First-NAME": [], "Last-NAME": [], "ORG": [], "DESG": [], "PHONE": [], "MAIL": [], "WEB": []}

    previous = "O"
    for token, label in info_array:
        bio_tag = label[0]
        label_tag = label[2:]
    
        text = parser(token, label_tag)
    
        if label_tag == "NAME":
            if bio_tag == "B":
                entities["First-NAME"].append(text)
            elif bio_tag == "I":
                entities["Last-NAME"].append(text)
            previous = bio_tag
        else:
            if bio_tag in ("B", "I"):
                if previous != label_tag:
                    entities[label_tag].append(text)
                else:
                    if label_tag in ("ORG", "DESG","PHONE"):
                        entities[label_tag][-1] = entities[label_tag][-1] + " " + text
                    else:
                        entities[label_tag][-1] = entities[label_tag][-1] + text
            previous = bio_tag

    return entities

