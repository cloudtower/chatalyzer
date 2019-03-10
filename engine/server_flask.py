#!/usr/bin/env python3

import re
import os
import sys
import json
import math
import urllib
import sqlite3
import binascii
import datetime
import unicodedata
from time import sleep
from flask import Flask
from flask import request
from html.parser import HTMLParser

server = Flask("wa_filter_backend")

@server.route("/api/getloadedfile")
def get_loaded_file():
    if table_prefix == None:
        return "-"
    return table_prefix

@server.route("/api/getnames")
def get_names():
    global act_wait

    while act_wait:
        sleep(0.1)

    if not act_cached:
        act_wait = True
        print("[+] No Cache for act. Computing...")
        compute_activity()

    return json.dumps(find_names())

def find_names():
    db_conn, db_cursor = getdbconnection()
    return list(db_cursor.execute("SELECT DISTINCT name FROM '%s' ORDER BY name" % (table_prefix + '-act')))

@server.route("/api/actraw")
def get_activity_raw():
    global act_wait

    while act_wait:
        sleep(0.1)

    if act_cached == False:
        act_wait = True
        compute_activity()

    pagesize = param_to_int(request.args.get("pagesize"),50)
    pagenumber = param_to_int(request.args.get("pagenumber"))
    asc = param_to_bool(request.args.get("asc"))
    sort = param_to_int(request.args.get("sortby"))
    filters = json.loads(request.args.get("filters"))

    sql = "SELECT * FROM '%s' " % (table_prefix + '-act')

    params = []
    first = True
    for key in filters.keys():
        if first:
            first = False
            sql += " WHERE %s=?" % (re.sub(r"\W","_",key))
        else:
            sql += " AND %s=?" % (re.sub(r"\W","_",key))
        params.append(filters[key])

    db_conn, db_cursor = getdbconnection()

    length = list(db_cursor.execute("SELECT COUNT(*) FROM(" + sql + ")", params))[0]

    sql += " ORDER BY %s %s LIMIT %s OFFSET %s" % (act_columnames[sort],sql_asc_bool[asc],str(pagesize),str(pagenumber * pagesize))

    return json.dumps((length,list(db_cursor.execute(sql, params))))


@server.route("/api/abn")
def get_activity_by_name():
    global act_wait
    db_conn, db_cursor = getdbconnection()

    while act_wait:
        sleep(0.1)

    if not act_cached:
        act_wait = True
        compute_activity()

    asc = param_to_bool(request.args.get("asc"))
    sort = param_to_int(request.args.get("sortby"))
    chartype_filter = param_to_string(request.args.get("chartype"),"none")
    
    mode = request.args.get("mode")

    if mode == "chart":
        db_output = activity_db_request("name")
        output = activity_filter(db_output)
        return json.dumps(([el[0] for el in db_output], output))
    else:
        db_output = list(db_cursor.execute("SELECT name as identifier, SUM(ispost) AS smessages, SUM(ismedia) as smedia, SUM(islogmsg) as slogmsg, SUM(words) AS swords, SUM(chars) as scharacters, SUM(emojis) semojis, SUM(puncts) as spuncts FROM '%s' GROUP BY name ORDER BY %s %s" % ((table_prefix + '-act'),atc_return_order[sort],sql_asc_bool[asc])))
        return json.dumps((list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT name FROM '%s' GROUP BY name)" % (table_prefix + '-act')))[0],db_output))

    db_conn.close()


@server.route("/api/abw")
def get_activity_by_weekday():
    labels = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    db_output = activity_db_request("weekday")

    output = activity_filter(db_output)

    return json.dumps((labels,output))


@server.route("/api/abdt")
def get_activity_by_daytime():
    labels = [str(i) + ":00" for i in range(0,24)]

    db_output = activity_db_request("hour")

    output = activity_filter(activity_db_pad([i for i in range(0,24)], db_output))

    return json.dumps((labels,output))


@server.route("/api/abt")
def get_activity_by_time():
    db_output = activity_db_request("date")

    aggr = param_to_int(request.args.get("aggregate"),7)

    output_inter = activity_filter(db_output,timemode=True)

    output = []

    for el in output_inter:
        aggr_list = []
        aggr_date = ("0" if len(el[1]) == 0 else el[1][0][0])
        aggr_sum = 0
        aggr_count = 1
        doavg = "per" in el[0]
        for el2 in el[1]:
            delta = ((datetime.datetime.strptime(el2[0],db_datetime)) - (datetime.datetime.strptime(aggr_date,db_datetime))).days
            if (delta < aggr):
                aggr_count += 1
                aggr_sum += el2[1]
            else:
                aggr_list.append((aggr_date,((float(aggr_sum) / float(aggr_count)) if doavg else aggr_sum)))
                aggr_sum = el2[1]
                aggr_date = el2[0]
                aggr_count = 1

        output.append((el[0],aggr_list))


    return json.dumps(([],output))


def activity_filter(db_output, timemode=False):
    output = []

    atc_return_order = ["identifier","smessages","smedia","slogmsg","swords","scharacters","semojis","spuncts"]
    all = [(el[4] + el[6] + el[7]) for el in db_output]

    if request.args.get("getmessages") == "true":
        output.append(("Messages", output_split((1,),db_output,timemode)))
    if request.args.get("getall") == "true":
        output.append(("Words", [(db_output[i][0], all[i]) for i in range(0, len(db_output))] if timemode else all))
    if request.args.get("getchars") == "true":
        output.append(("Characters", output_split((5,),db_output,timemode)))
    if request.args.get("getwords") == "true":
        output.append(("Words", output_split((4,),db_output,timemode)))
    if request.args.get("getemojis") == "true":
        output.append(("Emojis", output_split((6,),db_output,timemode)))
    if request.args.get("getpunct") == "true":
        output.append(("Puncts", output_split((7,),db_output,timemode)))
    if request.args.get("getmedia") == "true":
        output.append(("Media", output_split((2,),db_output,timemode)))
    if request.args.get("getlogs") == "true":
        output.append(("Log Messages", output_split((3,),db_output,timemode)))
    if request.args.get("getepmsg") == "true":
        output.append(("Emojis per Message", output_split((6,1),db_output,timemode,"/")))
    if request.args.get("getppmsg") == "true":
        output.append(("Puncts per Message", output_split((7,1),db_output,timemode,"/")))
    if request.args.get("getwpmsg") == "true":
        output.append(("Words per Message", output_split((4,1),db_output,timemode,"/")))
    if request.args.get("getepa") == "true":
        output.append(("Emojis per All", output_split((6,),db_output,timemode,"/a",all)))
    if request.args.get("getppa") == "true":
        output.append(("Puncts per All", output_split((7,),db_output,timemode,"/a",all)))
    if request.args.get("getwpa") == "true":
        output.append(("Words per All", output_split((4,),db_output,timemode,"/a",all)))
    if request.args.get("getepc") == "true":
        output.append(("Emojis per Character", output_split((6,5),db_output,timemode,"/")))
    if request.args.get("getppc") == "true":
        output.append(("Puncts per Character", output_split((7,5),db_output,timemode,"/")))
    if request.args.get("getwpc") == "true":
        output.append(("Words per Character", output_split((4,5),db_output,timemode,"/")))
    if request.args.get("getcpmsg") == "true":
        output.append(("Characters per Message", output_split((5,1),db_output,timemode,"/")))
    if request.args.get("getapmsg") == "true":
        output.append(("All per Message", output_split((1,),db_output,timemode,"a/",all)))
    if request.args.get("getcpa") == "true":
        output.append(("Characters per All", output_split((5,),db_output,timemode,"/a",all)))

    return output


def output_split(indexes, db_output, timemode=False, operator="", all=[]):
    if operator == "/":
        return [(db_output[i][0],safediv(db_output[i][indexes[0]],db_output[i][indexes[1]])) if timemode else safediv(db_output[i][indexes[0]],db_output[i][indexes[1]]) for i in range(0,len(db_output))]
    elif operator == "a/":
        return [(db_output[i][0],safediv(all[i],db_output[i][indexes[0]])) if timemode else safediv(all[i],db_output[i][indexes[0]]) for i in range(0,len(db_output))]
    elif operator == "/a":
        return [(db_output[i][0],safediv(db_output[i][indexes[0]],all[i])) if timemode else safediv(db_output[i][indexes[0]],all[i]) for i in range(0,len(db_output))]
    else:
        return [(el[0],el[indexes[0]]) if timemode else el[indexes[0]] for el in db_output]

def activity_db_request(group_by):
    sql = "SELECT %s as identifier, SUM(ispost) AS smessages, SUM(ismedia) as smedia, SUM(islogmsg) as slogmsg, SUM(words) AS swords, SUM(chars) as scharacters, SUM(emojis) semojis, SUM(puncts) as spuncts FROM '%s'" % (group_by, table_prefix + '-act')
    return db_request(sql, group_by, [])

def db_request(sql, group_by, params, setand = False):
    global act_wait

    while act_wait:
        sleep(0.1)

    if act_cached == False:
        act_wait = True
        compute_activity()

    db_conn, db_cursor = getdbconnection()

    person_filter = request.args.get("namefilter")
    if person_filter is not None:
        person_filter = HTMLParser().unescape(person_filter)

    if person_filter is not None and person_filter is not "":
        if setand:
            sql += " AND"
        else:
            sql += " WHERE"
            setand = True
        sql += " name=?"
        params += [person_filter]

    time_filter = request.args.get("timefilter")
    if time_filter is not None:
        split = time_filter.split("t")
        try:
            date_start = datetime.datetime.strptime(split[0],"%Y-%m-%d")
            date_end = datetime.datetime.strptime(split[1],"%Y-%m-%d")
            if setand:
                sql += " AND"
            else:
                sql += " WHERE"
                setand = True
            sql += " date BETWEEN '%s' AND '%s'" % (date_start, date_end)
        except:
            print("[!] Not a valid date!")

    weekday_filter = request.args.get("weekdayfilter")
    if weekday_filter is not None:
        if setand:
            sql += " AND"
        else:
            sql += " WHERE"
            setand = True
        sql += " weekday=?"
        params += [weekday_filter]

    daytime_filter = request.args.get("daytimefilter")
    if daytime_filter is not None:
        if setand:
            sql += " AND"
        else:
            sql += " WHERE"
            setand = True
        sql += " hour=?"
        params += [daytime_filter]

    sql += " GROUP BY %s" % group_by

    db_output = list(db_cursor.execute(sql,params))

    db_conn.close()

    return db_output


def activity_db_pad(labels, output, dontsort = False):
    if len(output) == 0:
        return output
    output_labels = [el[0] for el in output]
    for el in labels:
        if el not in output_labels:
            output.append((el,) + (0,) * (len(output[0]) - 1))
            output_labels.append(el)
    output = sorted(output, key = lambda x: x[0])
    return output


def compute_activity():
    global act_cached, act_wait
    f = open(fp)
    db_conn, db_cursor = getdbconnection()

    db_cursor.execute("CREATE TABLE '%s' (name text, date text, hour integer, weekday integer, ispost integer, ismedia integer, islogmsg integer, words integer, chars integer, emojis integer, puncts integer)" % (table_prefix + "-act"))

    weekday_last = 0
    hour_last = 0
    day_last = None

    log_msgs = []
    entries = []
    names = []

    for line in f:
        try:
            entry = ("unkown",datetime.date(2000,1,1),0,0,0,0,0,0,0,0,0)

            has_date = re.match(re_lang_filter_syntax, line) is not None
            has_name = re.match(re_lang_filter_log_syntax, line) is None
            is_media = re.search(re_lang_filter_media, line) is not None
            is_message = has_date

            if has_date:
                time = line.split(" - ")[0]
                hour_last = int(re.search(r"\, (\d{1,2})",time).group(1))
                date_last = datetime.datetime.strptime(time,lang_datetime)
                weekday_last = date_last.weekday()
                day_last = date_last.date()

            if not has_name:
                log_msgs.append((line,day_last,hour_last,weekday_last,0,0,1,0,0,0,0))
            else:
                if is_message:
                    linesplit = line.split(" - ", 1)[1].split(': ', 1)
                    name_last = linesplit[0]
                    linerest = linesplit[1]

                    if name_last not in names:
                        names.append(name_last)

                    if is_media:
                        entry = (name_last,day_last,hour_last,weekday_last,0,1,0,0,0,0,0)
                else:
                    linerest = line

                if not is_media:
                    linesplit = linerest.split(" ")
                    inter_punct = []
                    inter_emoji = []
                    filtered = []

                    for word in linesplit:
                        for part in re.split(r"([^\wäöü]+)",word):
                            inter_punct.append(part)

                    for word in inter_punct:
                        for part in re.split(r"("+re_lang_special_chars+r")",word):
                            inter_emoji.append(part)

                    for word in inter_emoji:
                        if re.match(r"[\wäöü]+",word) is None and re.match(re_lang_special_chars,word) is None:
                            for c in word:
                                filtered.append(c)
                        else:
                            filtered.append(word)

                    words = 0
                    emojis = 0
                    puncts = 0

                    for word in filtered:
                        if word != "\n" and word != "":
                            if re.match(r'\w+', word, re.UNICODE):
                                words += 1
                            elif re.match(re_lang_special_chars, word):
                                puncts += 1
                            elif len(word) == 1 and isemoji(word):
                                emojis += 1
                            else:
                                words += 1
                            
                    entry = (name_last,day_last,hour_last,weekday_last,int(is_message),0,0,words,len(linerest),emojis,puncts)

                entries.append(entry)
        except Exception as e:
            print("[!] Caught exception during activity computation: " + str(e))
    
    for element in log_msgs:
        for name in names:
            if name in element[0]:
                entries.append((name,) + element[1:])

    print("[-] Almost done, committing")
    db_cursor.executemany("INSERT INTO '%s' VALUES (?,?,?,?,?,?,?,?,?,?,?)" % (table_prefix + "-act"),entries)
    db_conn.commit()
    db_conn.close()
    print("[-] Done")

    act_cached = True
    act_wait = False



@server.route("/api/ubc")
def get_usage_by_character():
    global ubc_wait
    db_conn, db_cursor = getdbconnection()

    while ubc_wait:
        sleep(0.1)

    if ubc_cached == False:
        ubc_wait = True
        print("[+] No Cache for ubc. Computing...")
        compute_usage()
    
    pagesize = param_to_int(request.args.get("pagesize"),50)
    pagenumber = param_to_int(request.args.get("pagenumber"))
    sort = param_to_int(request.args.get("sortby"))
    stop = param_to_bool(request.args.get("stop"))
    asc = param_to_bool(request.args.get("asc"))
    chartype = request.args.get("type")

    return_order = ["word","usage"]

    if chartype == "emoji":
        db_output = list(db_cursor.execute("SELECT word, SUM(isemoji) as usage FROM '%s' WHERE isemoji=1 GROUP BY word ORDER BY %s %s LIMIT %s OFFSET %s" % ((table_prefix + '-ubw'),return_order[sort],sql_asc_bool[asc],str(pagesize),str(pagenumber * pagesize))))
        db_output = (list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT word FROM '%s' WHERE isemoji=1 GROUP BY word)" % (table_prefix + '-ubw')))[0],db_output)
    elif chartype == "puncts":
        db_output = list(db_cursor.execute("SELECT word, SUM(ispunct) as usage FROM '%s' WHERE ispunct=1 GROUP BY word ORDER BY %s %s LIMIT %s OFFSET %s" % ((table_prefix + '-ubw'),return_order[sort],sql_asc_bool[asc],str(pagesize),str(pagenumber * pagesize))))
        db_output = (list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT word FROM '%s' WHERE ispunct=1 GROUP BY word)" % (table_prefix + '-ubw')))[0],db_output)
    elif chartype == "uncat":
        db_output = list(db_cursor.execute("SELECT word, SUM(isuncat) as usage FROM '%s' WHERE isuncat=1 GROUP BY word ORDER BY %s %s LIMIT %s OFFSET %s" % ((table_prefix + '-ubw'),return_order[sort],sql_asc_bool[asc],str(pagesize),str(pagenumber * pagesize))))
        db_output = [(str(c[0]) + " = " + (str((c[0].encode("ascii","namereplace"))[3:-1]).lower())[2:-1] + " = " + str(c[0].encode("ascii","backslashreplace").lower())[3:-1], c[1]) for c in db_output]
        db_output = (list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT word FROM '%s' WHERE isuncat=1 GROUP BY word)" % (table_prefix + '-ubw')))[0],db_output)
    else:
        db_output = list(db_cursor.execute("SELECT word, SUM(isword) as usage FROM '%s' WHERE isword=1 GROUP BY word ORDER BY %s %s LIMIT %s OFFSET %s" % ((table_prefix + '-ubw'),return_order[sort],sql_asc_bool[asc],str(pagesize),str(pagenumber * pagesize))))
        db_output = (list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT word FROM '%s' WHERE isword=1 GROUP BY word)" % (table_prefix + '-ubw')))[0],db_output)

    db_conn.close()

    return json.dumps(db_output)


def ubw_db_request(word, group_by):
    return db_request("SELECT %s, (SUM(isword) + SUM(isemoji) + SUM(ispunct) + SUM(isuncat)) as usage FROM '%s' WHERE word=?" % (group_by, table_prefix + '-ubw'), group_by, [word], True)


@server.route("/api/ubw")
def get_usage_by_word():
    global ubc_wait
    db_conn, db_cursor = getdbconnection()

    while ubc_wait:
        sleep(0.1)

    if ubc_cached == False:
        ubc_wait = True
        print("[+] No Cache for ubc. Computing...")
        compute_usage()

    words = json.loads(request.args.get("words"))
    mode = param_to_string(request.args.get("mode"))

    if mode == "bydaytime":
        labels = [str(i) + ":00" for i in range(0,24)]
        return json.dumps((labels, [(word,[el[1] for el in activity_db_pad([i for i in range(0,24)], ubw_db_request(word, "hour"))]) for word in words]))
    elif mode == "byweekday":
        return json.dumps((["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"], [(word,[el[1] for el in activity_db_pad([i for i in range(0,7)], ubw_db_request(word, "weekday"))]) for word in words]))
    elif mode == "bytime":
        return json.dumps(([],[(word,[(el[0],el[1]) for el in ubw_db_request(word, "date")]) for word in words]))
    elif mode == "byname":
        names = [el[0] for el in find_names()]
        return json.dumps((names,[(word,[el[1] for el in activity_db_pad(names,ubw_db_request(word, "name"))]) for word in words]))
    elif mode == "total":
        return json.dumps([[word, list(db_cursor.execute("SELECT (SUM(isword) + SUM(isemoji) + SUM(ispunct) + SUM(isuncat)) as usage FROM '%s' WHERE word like ?" % (table_prefix + '-ubw'),(word,)))[0][0]] for word in words])


def compute_usage():
    global ubc_cached, ubc_wait
    db_conn, db_cursor = getdbconnection()

    db_cursor.execute("CREATE TABLE '%s' (name text, date text, hour integer, weekday integer, isword integer, isemoji integer, ispunct integer, isuncat integer, word text)" % (table_prefix + "-ubw"))

    weekday_last = 0
    hour_last = 0
    day_last = None
    name_last = "unknown"

    entries = []

    f = open(fp)
    for line in f:
        try:
            if re.search(re_lang_filter_media, line) is None:
                if re.match(re_lang_filter_log_syntax, line) is None:
                    entry = ("unkown",datetime.date(2000,1,1),0,0,0,0,0,0,"")

                    if re.search(re_lang_filter_syntax, line) is not None:
                        linesplit = line.split(" - ",1)
                        time = linesplit[0]
                        hour_last = int(re.search(r"\, (\d{1,2})",time).group(1))
                        date_last = datetime.datetime.strptime(time,lang_datetime)
                        weekday_last = date_last.weekday()
                        day_last = date_last.date()
                        linesplit = linesplit[1].split(': ', 1)
                        name_last = linesplit[0]
                        linerest = linesplit[1]
                    else:
                        linerest = line

                    linesplit = linerest.split(" ")
                    inter_punct = []
                    inter_emoji = []
                    filtered = []

                    for word in linesplit:
                        for part in re.split(r"([^\wäöü]+)",word):
                            inter_punct.append(part)

                    for word in inter_punct:
                        for part in re.split(r"("+re_lang_special_chars+r")",word):
                            inter_emoji.append(part)

                    for word in inter_emoji:
                        if re.match(r"[\wäöü]+",word) is None and re.match(re_lang_special_chars,word) is None:
                            for c in word:
                                filtered.append(c)
                        else:
                            filtered.append(word)

                    for word in filtered:
                        if word != "\n" and word != "":
                            word = word.lower()
                            if re.match(r'\w+', word, re.UNICODE):
                                entry = (name_last,day_last,hour_last,weekday_last,1,0,0,0,word)
                            elif re.match(re_lang_special_chars, word):
                                entry = (name_last,day_last,hour_last,weekday_last,0,0,1,0,word)
                            elif len(word) == 1 and isemoji(word):
                                entry = (name_last,day_last,hour_last,weekday_last,0,1,0,0,word)
                            else:
                                entry = (name_last,day_last,hour_last,weekday_last,0,0,0,1,word)
                                
                            entries.append(entry)

        except Exception as e:
            print("[!] Caught exception scanning ubw: " + str(e))

    print("[-] Almost done, committing")
    db_cursor.executemany("INSERT INTO '%s' VALUES (?,?,?,?,?,?,?,?,?)" % (table_prefix + "-ubw"),entries)
    db_conn.commit()
    db_conn.close()
    print("[-] Done")

    ubc_cached = True
    ubc_wait = False



@server.route("/api/loadfile")
def get_loadfile():
    filename = request.args.get("filename")
    if filename == None:
        return("No file specified.")
    return loadfile(filename)
    

def loadfile(filename):
    global fp, table_prefix

    try: 
        filename = HTMLParser().unescape(filename)
        print("[i] " + filename)
        table_prefix = re.split(r"[\/\\]",filename)[-1].split(".")[0]
        table_prefix = re.sub(r"\W","_",table_prefix)
        print("[i] New table prefix: " + table_prefix)
        f = open(filename)
        f.close()
        fp = filename
        resetcachedbits()
        return("Successfully loaded file.")
    except IOError:
        return("File not found.")


@server.route("/api/setlang")
def setlang():
    lang = request.args.get("lang")
    if lang == None:
        lang = "en"
    setdefaultlang(lang)
    return "Language successfully set."


def setdefaultlang(lang="en"):
    global re_lang_filter_syntax, re_lang_filter_log_syntax, re_lang_filter_media, re_lang_special_chars, lang_datetime, db_datetime
    if lang=="en":
        re_lang_filter_syntax = r"(\d{1,2}\/){2}\d{2}, \d{2}:\d{2} - .*"
        re_lang_filter_log_syntax = r"(\d{1,2}\/){2}\d{2}, \d{2}:\d{2} - ([^\:])*$"
        re_lang_filter_media = r"<Media omitted>"
        re_lang_special_chars = r"[\.\,\/\;\-\!\?\=\%\"\&\:\+\#\(\)\^\'\*\[\]\€\@\~\{\}\<\>\´\`\°]"
        lang_datetime = "%m/%d/%y, %H:%M"
    elif lang=="de":
        re_lang_filter_syntax = r"(\d{2}\.){2}\d{2}, \d{2}:\d{2} - .*"
        re_lang_filter_log_syntax = r"(\d{2}\.){2}\d{2}, \d{2}:\d{2} - ([^\:])*$"
        re_lang_filter_media = r"<Medien ausgeschlossen>"
        re_lang_special_chars = r"[\.\,\/\;\-\!\?\=\%\"\&\:\+\#\(\)\^\'\*\[\]\€\@\~\{\}\<\>\´\`\°]"
        lang_datetime = "%d.%m.%y, %H:%M"
    db_datetime = "%Y-%m-%d"

def resetcachedbits():
    global act_cached, act_wait, ubc_cached, ubc_wait

    db_conn = sqlite3.connect("chats.db")
    db_cursor = db_conn.cursor()

    act_cached = (len(list(db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",((table_prefix + "-act"),)))) > 0)
    act_wait = False
    ubc_cached = (len(list(db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?",((table_prefix + "-ubw"),)))) > 0)
    ubc_wait = False


def loadstopwords(lang="en"):
    global stopwords
    stopwords = []
    save = False
    try:
        f = open("stopwords.txt")
        for line in f:
            if save and line == "":
                save = False
            if save:
                stopwords.append(line.strip("\n"))
            if re.match(r"\[(\w+)\]",line) is not None:
                if re.match(r"\[(\w+)\]$",line).group(1) == lang:
                    save = True
    except IOError:
        print("[!] Error while reading stopwords file!")
    

def isemoji(ch):
    i = ord(ch)
    return (i >= 0x1f300 and i < 0x1f64f) or (i >= 0x1f681 and i < 0x1f6c5) or (i >= 0x1f30d and i < 0x1f567) or (i >= 0x2600 and i < 0x27C0) or (i >= 0x1f900 and i < 0x1fa00)


def getdbconnection():
    db_conn = sqlite3.connect("chats.db")
    db_cursor = db_conn.cursor()
    return (db_conn, db_cursor)


def safediv(num, denom):
    try:
        num = int(num)
        denom = int(denom)
    except (ValueError, TypeError):
        return 0
    if denom == 0:
        return 0
    else:
        res = (num / denom)
        if res < 1:
            return round(res, -int(math.floor(math.log10(abs(res)))) + 1)
        else:
            return round(res, 2)


def param_to_bool(param, default=False):
    if param == "true":
        return True
    elif param == "false":
        return False
    else:
        return default

def param_to_int(param, default=0):
    try:
        return int(param)
    except (ValueError, TypeError):
        return default

def param_to_string(param, default=""):
    if param == None:
        return default
    else:
        return param


act_columnames = ["name", "date", "hour", "weekday", "ispost", "ismedia", "islogmsg", "words", "chars", "emojis", "puncts"]
atc_return_order = ["identifier","smessages","smedia","slogmsg","swords","scharacters","semojis","spuncts"]
sql_asc_bool = { True: "ASC", False: "DESC" }
loadfile("/home/lion/Entwuerfe/Verschiedenes/res/WA_KK_3_fix.txt")
resetcachedbits()
setdefaultlang()
loadstopwords(lang="de")

if __name__ == "__main__":
    server.run()