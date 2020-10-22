import re
import math
import sqlite3
import datetime

from html.parser import HTMLParser

ACT_COLUMNAMES = ["name", "date", "hour", "weekday", "ispost", "ismedia", "islogmsg", "words", "chars", "emojis", "puncts"]
ACT_RETURN_ORDER = ["identifier", "smessages", "smedia", "slogmsg", "swords", "scharacters", "semojis", "spuncts"]
SQL_ASC_BOOL = {True: "ASC", False: "DESC"}


def find_names(api_state):
    _, db_cursor = getdbconnection()
    return list(db_cursor.execute("SELECT DISTINCT name FROM '{}' ORDER BY name".format(api_state.table_prefix + '-act')))


def activity_filter(db_output, request, timemode=False):
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
    if request.args.get("getcpw") == "true":
        output.append(("Characters per Word", output_split((5, 4), db_output, timemode, "/")))

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


def activity_db_request(group_by, api_state, request):
    sql = "SELECT {} as identifier, SUM(ispost) AS smessages, SUM(ismedia) as smedia, SUM(islogmsg) as slogmsg, SUM(words) AS swords, SUM(chars) as scharacters, SUM(emojis) semojis, SUM(puncts) as spuncts FROM '{}'".format(group_by, api_state.table_prefix + '-act')
    return db_request(sql, group_by, [], request)


def db_request(sql, group_by, params, request, setand=False, sql_postfix=""):
    def sql_and(setand, sql):
        sql += " AND" if setand else " WHERE"
        return True, sql

    db_conn, db_cursor = getdbconnection()

    person_filter = request.args.get("namefilter")
    if person_filter:
        person_filter = HTMLParser().unescape(person_filter)
        setand, sql = sql_and(setand, sql)
        sql += " name=?"
        params += [person_filter]

    time_filter = request.args.get("timefilter")
    if time_filter:
        split = time_filter.split("t")
        try:
            date_start = datetime.datetime.strptime(split[0], "%Y-%m-%d")
            date_end = datetime.datetime.strptime(split[1], "%Y-%m-%d")
            setand, sql = sql_and(setand, sql)
            sql += " date BETWEEN '{}' AND '{}'".format(date_start, date_end)
        except:
            print("[!] Not a valid date!")

    weekday_filter = request.args.get("weekdayfilter")
    if weekday_filter:
        setand, sql = sql_and(setand, sql)
        sql += " weekday=?"
        params += [weekday_filter]

    daytime_filter = request.args.get("daytimefilter")
    if daytime_filter:
        setand, sql = sql_and(setand, sql)
        sql += " hour=?"
        params += [daytime_filter]

    sql += " GROUP BY {}".format(group_by)

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


def ubc_db_request(api_state, request):
    pagesize = param_to_int(request.args.get("pagesize"), 50)
    pagenumber = param_to_int(request.args.get("pagenumber"))
    sort = param_to_int(request.args.get("sortby"))
    stop = param_to_bool(request.args.get("stop"))
    asc = param_to_bool(request.args.get("asc"))
    chartype = param_to_string(request.args.get("type"))
    return_order = ["word", "usage"]

    db_output = db_request("SELECT word, SUM(is{}) as usage FROM '{}' WHERE is{}=1".format(chartype, api_state.table_prefix + '-ubw', chartype), "word", [], request, True, " ORDER BY {} {} LIMIT {} OFFSET {}".format(return_order[sort], SQL_ASC_BOOL[asc], str(pagesize), str(pagenumber * pagesize)))
    output_len = db_request("SELECT COUNT(*) FROM (SELECT word FROM '{}' WHERE is{}=1".format(api_state.table_prefix + '-ubw', chartype), "word", [], request, True, ")")

    if chartype == "uncat":
        return output_len, [(str(c[0]) + " = " + (str((c[0].encode("ascii", "namereplace"))[3:-1]).lower())[2:-1] + " = " + str(c[0].encode("ascii", "backslashreplace").lower())[3:-1], c[1]) for c in db_output]
    else:
        return output_len, db_output


def ubw_db_request(word, group_by, api_state, request):
    return db_request("SELECT {}, (SUM(isword) + SUM(isemoji) + SUM(ispunct) + SUM(isuncat)) as usage FROM '{}' WHERE word=?".format(group_by, api_state.table_prefix + '-ubw'), group_by, [word], request, True)


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
    if not param:
        return default
    else:
        return re.sub(r"\W", "", param)
