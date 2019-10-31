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
    if table_prefix is None:
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
    _, db_cursor = getdbconnection()
    return list(db_cursor.execute("SELECT DISTINCT name FROM '%s' ORDER BY name" % (table_prefix + '-act')))

@server.route("/api/actraw")
def get_activity_raw():
    global act_wait

    while act_wait:
        sleep(0.1)

    if not act_cached:
        act_wait = True
        compute_activity()

    pagesize = param_to_int(request.args.get("pagesize"), 50)
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
            sql += " WHERE %s=?" % (re.sub(r"\W", "_", key))
        else:
            sql += " AND %s=?" % (re.sub(r"\W", "_", key))
        params.append(filters[key])

    _, db_cursor = getdbconnection()

    length = list(db_cursor.execute("SELECT COUNT(*) FROM(" + sql + ")", params))[0]

    sql += " ORDER BY %s %s LIMIT %s OFFSET %s" % (act_columnames[sort], sql_asc_bool[asc], str(pagesize), str(pagenumber * pagesize))

    return json.dumps((length, list(db_cursor.execute(sql, params))))


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
    chartype_filter = param_to_string(request.args.get("chartype"), "none")

    mode = request.args.get("mode")

    if mode == "chart":
        db_output = activity_db_request("name")
        output = activity_filter(db_output)
        return json.dumps(([el[0] for el in db_output], output))
    else:
        db_output = list(db_cursor.execute("SELECT name as identifier, SUM(ispost) AS smessages, SUM(ismedia) as smedia, SUM(islogmsg) as slogmsg, SUM(words) AS swords, SUM(chars) as scharacters, SUM(emojis) semojis, SUM(puncts) as spuncts FROM '%s' GROUP BY name ORDER BY %s %s" % ((table_prefix + '-act'), act_return_order[sort], sql_asc_bool[asc])))
        return json.dumps((list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT name FROM '%s' GROUP BY name)" % (table_prefix + '-act')))[0], db_output))

    db_conn.close()


@server.route("/api/abw")
def get_activity_by_weekday():
    labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    db_output = activity_db_request("weekday")

    output = activity_filter(db_output)

    return json.dumps((labels, output))


@server.route("/api/abdt")
def get_activity_by_daytime():
    labels = [str(i) + ":00" for i in range(0, 24)]

    db_output = activity_db_request("hour")

    output = activity_filter(activity_db_pad([i for i in range(0, 24)], db_output))

    return json.dumps((labels, output))


@server.route("/api/abt")
def get_activity_by_time():
    db_output = activity_db_request("date")

    aggr = param_to_int(request.args.get("aggregate"), 7)

    output_inter = activity_filter(db_output, timemode=True)

    output = []

    for el in output_inter:
        aggr_list = []
        aggr_date = ("0" if not el[1] else el[1][0][0])
        aggr_sum = 0
        aggr_count = 1
        doavg = "per" in el[0]
        for el2 in el[1]:
            delta = ((datetime.datetime.strptime(el2[0], db_datetime)) - (datetime.datetime.strptime(aggr_date, db_datetime))).days
            if delta < aggr:
                aggr_count += 1
                aggr_sum += el2[1]
            else:
                aggr_list.append((aggr_date, ((float(aggr_sum) / float(aggr_count)) if doavg else aggr_sum)))
                aggr_sum = el2[1]
                aggr_date = el2[0]
                aggr_count = 1

        output.append((el[0], aggr_list))


    return json.dumps(([], output))


def activity_filter(db_output, timemode=False):
    output = []

    sum_all = [(el[4] + el[6] + el[7]) for el in db_output]

    if request.args.get("getmessages") == "true":
        output.append(("Messages", output_split((1, ), db_output, timemode)))
    if request.args.get("getall") == "true":
        output.append(("Words", [(db_output[i][0], sum_all[i]) for i in range(0, len(db_output))] if timemode else sum_all))
    if request.args.get("getchars") == "true":
        output.append(("Characters", output_split((5, ), db_output, timemode)))
    if request.args.get("getwords") == "true":
        output.append(("Words", output_split((4, ), db_output, timemode)))
    if request.args.get("getemojis") == "true":
        output.append(("Emojis", output_split((6, ), db_output, timemode)))
    if request.args.get("getpunct") == "true":
        output.append(("Puncts", output_split((7, ), db_output, timemode)))
    if request.args.get("getmedia") == "true":
        output.append(("Media", output_split((2, ), db_output, timemode)))
    if request.args.get("getlogs") == "true":
        output.append(("Log Messages", output_split((3, ), db_output, timemode)))
    if request.args.get("getepmsg") == "true":
        output.append(("Emojis per Message", output_split((6, 1), db_output, timemode, "/")))
    if request.args.get("getppmsg") == "true":
        output.append(("Puncts per Message", output_split((7, 1), db_output, timemode, "/")))
    if request.args.get("getwpmsg") == "true":
        output.append(("Words per Message", output_split((4, 1), db_output, timemode, "/")))
    if request.args.get("getepa") == "true":
        output.append(("Emojis per All", output_split((6, ), db_output, timemode, "/a", sum_all)))
    if request.args.get("getppa") == "true":
        output.append(("Puncts per All", output_split((7, ), db_output, timemode, "/a", sum_all)))
    if request.args.get("getwpa") == "true":
        output.append(("Words per All", output_split((4, ), db_output, timemode, "/a", sum_all)))
    if request.args.get("getepc") == "true":
        output.append(("Emojis per Character", output_split((6, 5), db_output, timemode, "/")))
    if request.args.get("getppc") == "true":
        output.append(("Puncts per Character", output_split((7, 5), db_output, timemode, "/")))
    if request.args.get("getwpc") == "true":
        output.append(("Words per Character", output_split((4, 5), db_output, timemode, "/")))
    if request.args.get("getcpmsg") == "true":
        output.append(("Characters per Message", output_split((5, 1), db_output, timemode, "/")))
    if request.args.get("getapmsg") == "true":
        output.append(("All per Message", output_split((1, ), db_output, timemode, "a/", sum_all)))
    if request.args.get("getcpa") == "true":
        output.append(("Characters per All", output_split((5, ), db_output, timemode, "/a", sum_all)))

    return output


def output_split(indexes, db_output, timemode=False, operator="", sum_all=[]):
    if operator == "/":
        return [(db_output[i][0], safediv(db_output[i][indexes[0]], db_output[i][indexes[1]])) if timemode else safediv(db_output[i][indexes[0]], db_output[i][indexes[1]]) for i in range(0, len(db_output))]
    elif operator == "a/":
        return [(db_output[i][0], safediv(sum_all[i], db_output[i][indexes[0]])) if timemode else safediv(sum_all[i], db_output[i][indexes[0]]) for i in range(0, len(db_output))]
    elif operator == "/a":
        return [(db_output[i][0], safediv(db_output[i][indexes[0]], sum_all[i])) if timemode else safediv(db_output[i][indexes[0]], sum_all[i]) for i in range(0, len(db_output))]
    else:
        return [(el[0], el[indexes[0]]) if timemode else el[indexes[0]] for el in db_output]

def activity_db_request(group_by):
    sql = "SELECT %s as identifier, SUM(ispost) AS smessages, SUM(ismedia) as smedia, SUM(islogmsg) as slogmsg, SUM(words) AS swords, SUM(chars) as scharacters, SUM(emojis) semojis, SUM(puncts) as spuncts FROM '%s'" % (group_by, table_prefix + '-act')
    return db_request(sql, group_by, [])

def db_request(sql, group_by, params, setand=False, sql_postfix=""):
    global act_wait

    while act_wait:
        sleep(0.1)

    if not act_cached:
        act_wait = True
        compute_activity()

    def sql_and(setand, sql):
        sql += " AND" if setand else " WHERE"
        return True, sql

    db_conn, db_cursor = getdbconnection()

    person_filter = request.args.get("namefilter")
    if person_filter is not None:
        person_filter = HTMLParser().unescape(person_filter)

    if person_filter is not None and person_filter is not "":
        setand, sql = sql_and(setand, sql)
        sql += " name=?"
        params += [person_filter]

    time_filter = request.args.get("timefilter")
    if time_filter is not None:
        split = time_filter.split("t")
        try:
            date_start = datetime.datetime.strptime(split[0], "%Y-%m-%d")
            date_end = datetime.datetime.strptime(split[1], "%Y-%m-%d")
            setand, sql = sql_and(setand, sql)
            sql += " date BETWEEN '%s' AND '%s'" % (date_start, date_end)
        except:
            print("[!] Not a valid date!")

    weekday_filter = request.args.get("weekdayfilter")
    if weekday_filter is not None:
        setand, sql = sql_and(setand, sql)
        sql += " weekday=?"
        params += [weekday_filter]

    daytime_filter = request.args.get("daytimefilter")
    if daytime_filter is not None:
        setand, sql = sql_and(setand, sql)
        sql += " hour=?"
        params += [daytime_filter]

    sql += " GROUP BY %s" % group_by

    db_output = list(db_cursor.execute(sql + sql_postfix, params))

    db_conn.close()

    return db_output


def activity_db_pad(labels, output, dontsort=False):
    if not output:
        return output
    output_labels = [el[0] for el in output]
    for el in labels:
        if el not in output_labels:
            output.append((el, ) + (0, ) * (len(output[0]) - 1))
            output_labels.append(el)
    output = sorted(output, key=lambda x: x[0])
    return output


def compute_activity():
    global act_cached, act_wait
    db_conn, db_cursor = getdbconnection()

    db_cursor.execute("CREATE TABLE '%s' (name text, date text, hour integer, weekday integer, ispost integer, ismedia integer, islogmsg integer, words integer, chars integer, emojis integer, puncts integer)" % (table_prefix + "-act"))

    weekday_last = 0
    hour_last = 0
    day_last = None

    log_msgs = []
    entries = []
    names = []

    name_last = "unknown"

    with open(fp, encoding="utf-8") as f:
        for line in f:
            try:
                entry = ("unknown", datetime.date(2000, 1, 1), 0, 0, 0, 0, 0, 0, 0, 0, 0)

                has_date = re.match(re_lang_filter_syntax, line) is not None
                has_name = re.match(re_lang_filter_log_syntax, line) is None
                is_media = re.search(re_lang_filter_media, line) is not None
                is_message = has_date

                if has_date:
                    time = line.split(" - ")[0]
                    hour_last = int(re.search(r"\, (\d{1,2})", time).group(1))
                    date_last = datetime.datetime.strptime(time, lang_datetime)
                    weekday_last = date_last.weekday()
                    day_last = date_last.date()

                if not has_name:
                    log_msgs.append((line, day_last, hour_last, weekday_last, 0, 0, 1, 0, 0, 0, 0))
                else:
                    if is_message:
                        linesplit = line.split(" - ", 1)[1].split(': ', 1)
                        name_last = linesplit[0]
                        linerest = linesplit[1]

                        if name_last not in names:
                            names.append(name_last)

                        if is_media:
                            entry = (name_last, day_last, hour_last, weekday_last, 0, 1, 0, 0, 0, 0, 0)
                    else:
                        linerest = line

                    if not is_media:
                        linesplit = linerest.split(" ")
                        inter_punct = []
                        inter_emoji = []
                        filtered = []

                        for word in linesplit:
                            for part in re.split(r"([^\wäöü]+)", word):
                                inter_punct.append(part)

                        for word in inter_punct:
                            for part in re.split(r"("+re_lang_special_chars+r")", word):
                                inter_emoji.append(part)

                        for word in inter_emoji:
                            if re.match(r"[\wäöü]+", word) is None and re.match(re_lang_special_chars, word) is None:
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

                        entry = (name_last, day_last, hour_last, weekday_last, int(is_message), 0, 0, words, len(linerest), emojis, puncts)

                    entries.append(entry)
            except Exception as e:
                print("[!] Caught exception during activity computation: " + str(e))

    for element in log_msgs:
        for name in names:
            if name in element[0]:
                entries.append((name, ) + element[1:])

    print("[-] Almost done, committing")
    db_cursor.executemany("INSERT INTO '%s' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" % (table_prefix + "-act"), entries)
    db_conn.commit()
    db_conn.close()
    print("[-] Done")

    act_cached = True
    act_wait = False



def ubc_db_request():
    pagesize = param_to_int(request.args.get("pagesize"), 50)
    pagenumber = param_to_int(request.args.get("pagenumber"))
    sort = param_to_int(request.args.get("sortby"))
    stop = param_to_bool(request.args.get("stop"))
    asc = param_to_bool(request.args.get("asc"))
    chartype = request.args.get("type")
    return_order = ["word", "usage"]

    db_output = db_request("SELECT word, SUM(is%s) as usage FROM '%s' WHERE is%s=1" % (chartype, table_prefix + '-ubw', chartype), "word", [], True, " ORDER BY %s %s LIMIT %s OFFSET %s" % (return_order[sort], sql_asc_bool[asc], str(pagesize), str(pagenumber * pagesize)))
    output_len = db_request("SELECT COUNT(*) FROM (SELECT word FROM '%s' WHERE is%s=1" % (table_prefix + '-ubw', chartype), "word", [], True, ")")
    if chartype == "uncat":
        return output_len, [(str(c[0]) + " = " + (str((c[0].encode("ascii", "namereplace"))[3:-1]).lower())[2:-1] + " = " + str(c[0].encode("ascii", "backslashreplace").lower())[3:-1], c[1]) for c in db_output]
    else:
        return output_len, db_output

@server.route("/api/ubc")
def get_usage_by_character():
    global ubc_wait

    while ubc_wait:
        sleep(0.1)

    if ubc_cached == False:
        ubc_wait = True
        print("[+] No Cache for ubc. Computing...")
        compute_usage()

    db_output = ubc_db_request()

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
        labels = [str(i) + ":00" for i in range(0, 24)]
        return json.dumps((labels, [(word, [el[1] for el in activity_db_pad([i for i in range(0, 24)], ubw_db_request(word, "hour"))]) for word in words]))
    elif mode == "byweekday":
        return json.dumps((["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], [(word, [el[1] for el in activity_db_pad([i for i in range(0, 7)], ubw_db_request(word, "weekday"))]) for word in words]))
    elif mode == "bytime":
        return json.dumps(([], [(word, [(el[0], el[1]) for el in ubw_db_request(word, "date")]) for word in words]))
    elif mode == "byname":
        names = [el[0] for el in find_names()]
        return json.dumps((names, [(word, [el[1] for el in activity_db_pad(names, ubw_db_request(word, "name"))]) for word in words]))
    elif mode == "total":
        return json.dumps([[word, list(db_cursor.execute("SELECT (SUM(isword) + SUM(isemoji) + SUM(ispunct) + SUM(isuncat)) as usage FROM '%s' WHERE word like ?" % (table_prefix + '-ubw'), (word, )))[0][0]] for word in words])


def compute_usage():
    global ubc_cached, ubc_wait
    db_conn, db_cursor = getdbconnection()

    db_cursor.execute("CREATE TABLE '%s' (name text, date text, hour integer, weekday integer, isword integer, isemoji integer, ispunct integer, islink integer, isuncat integer, word text)" % (table_prefix + "-ubw"))

    weekday_last = 0
    hour_last = 0
    day_last = None
    name_last = "unknown"

    entries = []

    with open(fp, encoding="utf-8") as f:
        for line in f:
            try:
                if re.search(re_lang_filter_media, line) is None:
                    if re.match(re_lang_filter_log_syntax, line) is None:
                        entry = ("unkown", datetime.date(2000, 1, 1), 0, 0, 0, 0, 0, 0, 0, "")

                        if re.search(re_lang_filter_syntax, line) is not None:
                            linesplit = line.split(" - ", 1)
                            time = linesplit[0]
                            hour_last = int(re.search(r"\, (\d{1,2})", time).group(1))
                            date_last = datetime.datetime.strptime(time, lang_datetime)
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
                        hyperlinks = []

                        # handle hyperlinks
                        for word in linesplit:
                            hyperlink = re.search(r"https?://[a-zA-Z0-9_!\*'\(\);%@\&=\+\$,/\?\#\[\]\.\~\-]*", word)
                            if hyperlink is not None:
                                hyperlinks.append(hyperlink.group(0))
                                inter_punct.append(word[:hyperlink.span(0)[0]])
                                inter_punct.append(word[hyperlink.span(0)[1]:])
                            else:
                                for part in re.split(r"([^\wäöü]+)", word):
                                    inter_punct.append(part)

                        for word in inter_punct:
                            for part in re.split(r"("+re_lang_special_chars+r")", word):
                                inter_emoji.append(part)

                        for i, word in enumerate(inter_emoji):
                            # handle keycap emoji sequences
                            if i < len(inter_emoji) - 1 and len(inter_emoji[i + 1]) > 0 and ord(inter_emoji[i + 1][0]) == 0x20e3:
                                if len(word) > 1:
                                    filtered.append(word[:-1])
                                filtered.append(word[-1] + inter_emoji[i + 1][0])
                                inter_emoji[i + 1] = inter_emoji[i + 1][1:]
                            else:
                                if re.match(r"[\wäöü]+$", word) is None and re.match(re_lang_special_chars + r"$", word) is None:
                                    j = 0
                                    while j < len(word):
                                        toappend = word[j]
                                        # handle multiple emojis joined by zero-width space
                                        if j < len(word) - 1 and word[j + 1] == 0x200d:
                                            while j < len(word) - 2 and word[j + 1] == 0x200d:
                                                toappend += word[j + 1:j + 3]
                                                j += 2
                                        # handle emojis with skin color modifier and regional identifiers
                                        elif j < len(word) - 1 and (isfitzpatrickemoji(word[j + 1]) or isregionalindicator(word[j + 1])):
                                            toappend += word[j + 1]
                                            j += 1
                                        filtered.append(toappend)
                                        j += 1
                                else:
                                    filtered.append(word)

                        for word in filtered:
                            if word != "\n" and word != "":
                                word = word.lower()
                                if re.match(r'\w+$', word, re.UNICODE):
                                    entry = (name_last, day_last, hour_last, weekday_last, 1, 0, 0, 0, 0, word)
                                elif re.match(re_lang_special_chars, word):
                                    entry = (name_last, day_last, hour_last, weekday_last, 0, 0, 1, 0, 0, word)
                                elif len(word) <= 2 and isemoji(word):
                                    entry = (name_last, day_last, hour_last, weekday_last, 0, 1, 0, 0, 0, word)
                                else:
                                    entry = (name_last, day_last, hour_last, weekday_last, 0, 0, 0, 0, 1, word)

                                entries.append(entry)

                        for word in hyperlinks:
                            entries.append((name_last, day_last, hour_last, weekday_last, 0, 0, 0, 1, 0, word))

            except Exception as e:
                print("[!] Caught exception scanning ubw: " + str(e))

    print("[-] Almost done, committing")
    db_cursor.executemany("INSERT INTO '%s' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" % (table_prefix + "-ubw"), entries)
    db_conn.commit()
    db_conn.close()
    print("[-] Done")

    ubc_cached = True
    ubc_wait = False


@server.route("/api/getoptions")
def get_settings():
    key = param_to_string(request.args.get("key"), None)

    if key is None:
        return json.dumps(settings_global)
    else:
        try:
            return json.dumps(settings_global[key])
        except KeyError:
            return json.dumps(settings_global)


@server.route("/api/setoption")
def set_setting():
    global settings_global

    key = param_to_string(request.args.get("key"))
    value = param_to_string(request.args.get("value"))

    try:
        settings_global[key]["selected"] = value
    except KeyError:
        return "Error: no such option"

    try:
        with open(default_settings_file, "w") as f:
            f.write(json.dumps(settings_global))
        return "Success"
    except IOError as e:
        print("[!] Error writing config file!")
        print(e)
        return "Error: IOError"


def parse_config_file():
    global settings_global

    try:
        with open(default_settings_file) as f:
            settings_json = f.read()
    except IOError:
        print("[!] Error: Config file not found!")
        settings_json = ""

    try:
        settings_global = json.loads(settings_json)
    except json.decoder.JSONDecodeError as e:
        print("[!] Encountered error while parsing settings:")
        print(e)
        settings_global = default_settings

    for key, value in settings_global.items():
        parse_config(key, int(value["selected"]))

def parse_config(key, index):
    if key == "default_lang":
        try:
            setdefaultlang(settings_global["default_lang"]["options"][index])
        except IndexError:
            setdefaultlang()

@server.route("/api/loadfile")
def get_loadfile():
    filename = request.args.get("filename")
    if filename == None:
        return "No file specified."
    return loadfile(filename)


def loadfile(filename):
    global fp, table_prefix

    print("[i] " + filename)
    table_prefix = re.split(r"[\/\\]", filename)[-1].split(".")[0]
    table_prefix = re.sub(r"\W", "_", table_prefix)
    print("[i] New table prefix: " + table_prefix)
    if not os.path.isfile(filename):
        print("[!] File {} not found!".format(filename))
        table_prefix = None
        return "File not found."
    fp = filename
    resetcachedbits()
    return "Successfully loaded file."


@server.route("/api/getlang")
def getlang():
    return lang_global

@server.route("/api/setlang")
def setlang():
    lang = param_to_string(request.args.get("lang"), "en")
    setdefaultlang(lang)
    return "Language successfully set."


def setdefaultlang(lang="en"):
    global re_lang_filter_syntax, re_lang_filter_log_syntax, re_lang_filter_media, re_lang_special_chars, lang_datetime, db_datetime, lang_global
    if lang == "en":
        re_lang_filter_syntax = r"(\d{1,2}\/){2}\d{2}, \d{2}:\d{2} - .*"
        re_lang_filter_log_syntax = r"(\d{1,2}\/){2}\d{2}, \d{2}:\d{2} - ([^\:])*$"
        re_lang_filter_media = r"<Media omitted>"
        re_lang_special_chars = r"[\.\,\/\;\-\!\?\=\%\"\&\:\+\#\(\)\^\'\*\[\]\€\@\~\{\}\<\>\´\`\°\\\|]"
        lang_datetime = "%m/%d/%y, %H:%M"
        lang_global = "en"
    elif lang == "de":
        re_lang_filter_syntax = r"(\d{2}\.){2}\d{2}, \d{2}:\d{2} - .*"
        re_lang_filter_log_syntax = r"(\d{2}\.){2}\d{2}, \d{2}:\d{2} - ([^\:])*$"
        re_lang_filter_media = r"<Medien ausgeschlossen>"
        re_lang_special_chars = r"[\.\,\/\;\-\!\?\=\%\"\&\:\+\#\(\)\^\'\*\[\]\€\@\~\{\}\<\>\´\`\°\\\|]"
        lang_datetime = "%d.%m.%y, %H:%M"
        lang_global = "de"
    db_datetime = "%Y-%m-%d"

def resetcachedbits():
    global act_cached, act_wait, ubc_cached, ubc_wait

    db_conn = sqlite3.connect("chats.db")
    db_cursor = db_conn.cursor()

    act_cached = (len(list(db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ((table_prefix + "-act"), )))) > 0)
    act_wait = False
    ubc_cached = (len(list(db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", ((table_prefix + "-ubw"), )))) > 0)
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
            if re.match(r"\[(\w+)\]", line) is not None:
                if re.match(r"\[(\w+)\]$", line).group(1) == lang:
                    save = True
    except IOError:
        print("[!] Error while reading stopwords file!")


def isemoji(ch):
    if len(ch) > 1:
        return all([isemoji(c) for c in ch])

    i = ord(ch)
    return (i in range(0x1f600, 0x1f650) # Emojis
        or i in range(0x1f680, 0x1f700) # Transport and Map Symbols
        or i in range(0x1f300, 0x1f600) # Miscellaneous Symbols and Pictographs
        or i in range(0x2000, 0x2070) # General Punctuation
        or i == 0x20e3 # Combining Enclosing Keycap
        or i in range(0x30, 0x40) # Numbers (for enclosed combinations)
        or i in range(0x2190, 0x2200) # Arrows
        or i in range(0x2300, 0x2400) # Miscellaneous Technical
        or i in range(0x25a0, 0x2600) # Geometric Shapes
        or i in range(0x2600, 0x2700) # Miscellaneous Symbols
        or i in range(0x2700, 0x27C0) # Dingbats
        or i in range(0x2b00, 0x2c00) # Miscellaneous Symbols and Arrows
        or i in range(0x3200, 0x3300) # Enclosed CJK Letters and Months
        or i in range(0x1f900, 0x1fa00) # Supplemental Symbols and Pictographs
        or i in range(0x1f100,0x1f200) # Enclosed Alphanumeric Supplement
        or i in range(0x1f200, 0x1f300)) # Enclosed Ideographic Supplement

def isfitzpatrickemoji(ch):
    i = ord(ch)
    return (i in range(0x1f3fb, 0x1f400))

def isregionalindicator(ch):
    i = ord(ch)
    return (i in range(0x1f1e6, 0x1f200))

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
            if not res == 0:
                return round(res, -int(math.floor(math.log10(abs(res)))) + 1)
            else:
                return 0
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
act_return_order = ["identifier", "smessages", "smedia", "slogmsg", "swords", "scharacters", "semojis", "spuncts"]
sql_asc_bool = {True: "ASC", False: "DESC"}
#loadfile("/home/lion/Entwuerfe/Verschiedenes/res/WA_KK_3_fix.txt")
#resetcachedbits()
table_prefix = None
default_settings_file = "../settings.conf"
default_settings = {
    "default_lang": {
        "desc": "Default Language",
        "options": ["en", "de"],
        "selected": "0"
    },
    "color_scheme": {
        "desc": "Color Scheme",
        "options": ["dark"],
        "selected": "0"
    }
}
parse_config_file()

if __name__ == "__main__":
    server.run()