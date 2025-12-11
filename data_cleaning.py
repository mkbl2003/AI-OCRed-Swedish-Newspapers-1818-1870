import os
import re
transcript_path = "transcribed/WEXJÖBLADET 1835-09-18" # change this path as needed
clean_path = "transcribed/data/clean-transcripts/WEXJÖBLADET 1835-09-18" # change this path as needed

def create_directories():
    try:
        os.makedirs(clean_path, exist_ok=True)
    except OSError:
        print("%s already exists" % clean_path)
    else:
        print("%s created" % clean_path)

    for directory in os.listdir(transcript_path):
        tmp_path = clean_path + directory
        try:
            os.mkdir(tmp_path)
        except OSError:
            print("%s already exists" % tmp_path)
        else:
            print("%s created" % tmp_path)

def clean_text(text):
    expr = r'</?sw>|</?fr>|</? ?i ?>|</?big>|</?small>|</?aq>|</?sc>|</?init>|</? ?b ?>|</?sup>|</?sub>|</?u>|</?v>'
    return re.sub(expr, "", text)

def clean():
    for file_name in os.listdir(transcript_path):
            tmp_path = transcript_path + '/' + file_name
            write_file = clean_path + '/' + file_name
            with open(tmp_path , "r", encoding ="utf-8-sig") as file:
                contents = file.read()

            clean_contents = clean_text(contents)

            with open(write_file, 'w', encoding ="utf-8-sig") as file:
                file.write(clean_contents)

clean()
