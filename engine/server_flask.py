#!/usr/bin/env python3

import re
import os
import sys
import json
import datetime

from flask import Flask
from flask import request

from chat_parsing import compute_usage_telegram, compute_usage_whatsapp, compute_activity_telegram, compute_activity_whatsapp
from db_utils import *

DEFAULT_SETTINGS_FILE = "../settings.conf"
DEFAULT_SETTINGS = {
    "default_lang": {
        "desc": "Default Language",
        "options": ["en", "de"],
        "selected": "0"
    },
    "default_dev": {
        "desc": "Default device",
        "options": ["android", "ios"],
        "selected": "0"
    },
    "default_chat": {
        "desc": "Default Chat Application",
        "options": ["whatsapp", "telegram"],
        "selected": "0"
    },
    "color_scheme": {
        "desc": "Color Scheme",
        "options": ["dark"],
        "selected": "0"
    }
}

server = Flask("chatalyzer_backend")

class APIState():
    def __init__(self):
        self.table_prefix = None
        self.fp = None
        db_curs, db_conn = getdbconnection()

        if not len(list(db_curs.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='chats'"))):
            db_curs.execute("CREATE TABLE 'chats' (prefix text, start_date text, end_date integer, total_msg integer, avg_msg_daily integer, lang text)")

        self.parse_config_file()
        self.setlang()
        self.loadstopwords()

    def loadstopwords(self):
        self.stopwords = dict()
        lang_curr = ""

        try:
            f = open("stopwords.txt")
            for line in f:
                if line[0] == "#":
                    lang_curr = line[1:-1]
                    self.stopwords[lang_curr] = []
                else:
                    self.stopwords[lang_curr].append(line.strip("\n"))
        except IOError:
            print("[!] Error while reading stopwords file!")

    def setlang(self, lang=None, dev=None, chat=None):
        if lang:
            self.lang_global = lang
        if dev:
            self.dev_global = dev
        if chat:
            self.chat_global = chat

        if self.lang_global == "en":
            self.re_lang_filter_syntax = r"((\d{1,2}\/){2}\d{2}, \d{2}:\d{2}) - ([^\:]+): .*"
            self.re_lang_filter_log_syntax = r"((\d{1,2}\/){2}\d{2}, \d{2}:\d{2}) - ([^\:])*$"
            self.re_lang_filter_media = r"<Media omitted>"
            self.re_lang_special_chars = r"[\.\,\/\;\-\!\?\=\%\"\&\:\+\#\(\)\^\'\*\[\]\€\@\~\{\}\<\>\´\`\°\\\|]"
            self.lang_datetime = "%m/%d/%y, %H:%M"
        elif self.lang_global == "de":
            if self.dev_global == "ios":
                self.re_lang_filter_syntax = r"\[((\d{2}\.){2}\d{2}, \d{2}:\d{2}:\d{2})\] ([^\:]+): .*"
                self.re_lang_filter_log_syntax = r"\[((\d{2}\.){2}\d{2}, \d{2}:\d{2}:\d{2})\] ([^\:]+)$"
                self.re_lang_filter_media = r"<Video weggelassen>|<Audio weggelassen>|<Bild weggelassen>"
                self.lang_datetime = "%d.%m.%y, %H:%M:%S"
            else:
                self.re_lang_filter_syntax = r"((\d{2}\.){2}\d{2}, \d{2}:\d{2}) - ([^\:]+): .*"
                self.re_lang_filter_log_syntax = r"((\d{2}\.){2}\d{2}, \d{2}:\d{2}) - ([^\:])*$"
                self.re_lang_filter_media = r"<Medien ausgeschlossen>|<Medien weggelassen>"
                self.lang_datetime = "%d.%m.%y, %H:%M"
            self.re_lang_special_chars = r"[\.\,\/\;\-\!\?\=\%\"\&\:\+\#\(\)\^\'\*\[\]\€\@\~\{\}\<\>\´\`\°\\\|]"

        self.textemojis = ["^^", ":)", ";)", ":D", "xD", ";P", ":P", ";D", ":-)", ";-)", ":-D", ":d", ";d", "<3", "-.-", ":(", ":/", ">_<"]
        self.re_textemojis = r"|".join([re.escape(el) for el in self.textemojis])
        self.db_datetime = "%Y-%m-%d"

    def parse_config_file(self):
        try:
            with open(DEFAULT_SETTINGS_FILE) as f:
                settings_json = f.read()
        except IOError:
            print("[!] Error: Config file not found!")
            settings_json = ""

        self.settings_global = DEFAULT_SETTINGS
        try:
            self.settings_global.update(json.loads(settings_json))
        except json.decoder.JSONDecodeError as e:
            print("[!] Encountered error while parsing settings:", e)
            self.settings_global = DEFAULT_SETTINGS

        for key, value in self.settings_global.items():
            self.parse_config(key, int(value["selected"]))

    def parse_config(self, key, index):
        if key == "default_lang":
            self.lang_global = self.settings_global["default_lang"]["options"][index]
        elif key == "default_chat":
            self.chat_global = self.settings_global["default_chat"]["options"][index]
        elif key == "default_dev":
            self.dev_global = self.settings_global["default_dev"]["options"][index]

    def loadfile(self, prefix):
        self.table_prefix = prefix
        return "Successfully loaded file."

    def chat_check(self, filename):
        if self.chat_global == "telegram":
            return 0
        with open(filename, encoding="utf-8") as f:
            for line in f:
                if re.match(api_state.re_lang_filter_syntax, line):
                    return 0
        return 1

    def loadnewfile(self, filename):
        print("[i] " + filename)
        if not os.path.isfile(filename):
            print("[!] File {} not found!".format(filename))
            return (1, "File not found.", "")

        if self.chat_check(filename) > 0:
            return (2, "Chat check failed.", "")

        self.fp = filename

        if self.chat_global == "telegram":
            compute_activity_telegram(self)
            compute_usage_telegram(self)
        else:
            compute_activity_whatsapp(self)
            compute_usage_whatsapp(self)

        db_conn, db_curs = getdbconnection()

        act_total = list(db_curs.execute("SELECT COUNT(*) FROM '{}-act'".format(self.table_prefix)))[0][0]
        start_date = list(db_curs.execute("SELECT date FROM '{}-act' LIMIT 1".format(self.table_prefix)))[0][0]
        end_date = list(db_curs.execute("SELECT date FROM '{}-act' ORDER BY date DESC LIMIT 1".format(self.table_prefix)))[0][0]
        total_days = (datetime.datetime.fromisoformat(end_date) - datetime.datetime.fromisoformat(start_date)).days + 1

        db_curs.execute("INSERT INTO 'chats' VALUES (?, ?, ?, ?, ?, ?)", (self.table_prefix, start_date, end_date, act_total, "{:.2f}".format(act_total / total_days), self.lang_global))
        db_conn.commit()

        return (0, "Successfully loaded file.", self.table_prefix)


@server.route("/api/getloadedfile")
def get_loaded_file():
    return api_state.table_prefix if api_state.table_prefix else "-"


@server.route("/api/getnames")
def get_names():
    return json.dumps(find_names(api_state))


@server.route("/api/actraw")
def get_activity_raw():
    pagesize = param_to_int(request.args.get("pagesize"), 50)
    pagenumber = param_to_int(request.args.get("pagenumber"))
    asc = param_to_bool(request.args.get("asc"))
    sort = param_to_int(request.args.get("sortby"))
    filters = json.loads(request.args.get("filters"))

    sql = "SELECT * FROM '{}' ".format(api_state.table_prefix + '-act')

    params = []
    first = True
    for key in filters.keys():
        if first:
            first = False
            sql += " WHERE {}=?".format(re.sub(r"\W", "_", key))
        else:
            sql += " AND {}=?".format(re.sub(r"\W", "_", key))
        params.append(filters[key])

    _, db_cursor = getdbconnection()

    length = list(db_cursor.execute("SELECT COUNT(*) FROM(" + sql + ")", params))[0]

    sql += " ORDER BY {} {} LIMIT {} OFFSET {}".format(ACT_COLUMNAMES[sort], SQL_ASC_BOOL[asc], pagesize, (pagenumber * pagesize))

    return json.dumps((length, list(db_cursor.execute(sql, params))))


@server.route("/api/abn")
def get_activity_by_name():
    db_conn, db_cursor = getdbconnection()

    asc = param_to_bool(request.args.get("asc"))
    sort = param_to_int(request.args.get("sortby"))
    pagesize = param_to_int(request.args.get("pagesize"), 50)
    pagenumber = param_to_int(request.args.get("pagenumber"))
    chartype_filter = param_to_string(request.args.get("chartype"), "none")

    mode = request.args.get("mode")

    if mode == "chart":
        db_output = activity_db_request("name", api_state, request)
        output = activity_filter(db_output, request)
        return json.dumps(([el[0] for el in db_output], output))
    else:
        db_output = list(db_cursor.execute("SELECT name as identifier, SUM(ispost) AS smessages, SUM(ismedia) as smedia, SUM(islogmsg) as slogmsg, SUM(words) AS swords, SUM(chars) as scharacters, SUM(emojis) semojis, SUM(puncts) as spuncts FROM '{}' GROUP BY name ORDER BY {} {} LIMIT {} OFFSET {}".format((api_state.table_prefix + '-act'), ACT_RETURN_ORDER[sort], SQL_ASC_BOOL[asc], pagesize, (pagenumber * pagesize))))
        return json.dumps((list(db_cursor.execute("SELECT COUNT(*) FROM (SELECT name FROM '{}' GROUP BY name)".format(api_state.table_prefix + '-act')))[0], db_output))

    db_conn.close()


@server.route("/api/abw")
def get_activity_by_weekday():
    labels = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    db_output = activity_db_request("weekday", api_state, request)

    output = activity_filter(db_output, request)

    return json.dumps((labels, output))


@server.route("/api/abdt")
def get_activity_by_daytime():
    labels = [str(i) + ":00" for i in range(0, 24)]

    db_output = activity_db_request("hour", api_state, request)

    output = activity_filter(activity_db_pad(list(range(24)), db_output), request)

    return json.dumps((labels, output))


@server.route("/api/abt")
def get_activity_by_time():
    db_output = activity_db_request("date", api_state, request)

    aggr = param_to_int(request.args.get("aggregate"), 7)

    output_inter = activity_filter(db_output, request, timemode=True)

    output = []

    for el in output_inter:
        aggr_list = []
        aggr_date = ("0" if not el[1] else el[1][0][0])
        aggr_sum = 0
        aggr_count = 1
        doavg = "per" in el[0]

        for el2 in el[1]:
            delta = ((datetime.datetime.strptime(el2[0], api_state.db_datetime)) - (datetime.datetime.strptime(aggr_date, api_state.db_datetime))).days
            
            if delta < aggr:
                aggr_count += 1
                aggr_sum += el2[1]
            else:
                aggr_list.append((aggr_date, ((float(aggr_sum) / float(aggr_count)) if doavg else aggr_sum)))
                aggr_sum = el2[1]
                aggr_date = el2[0]
                aggr_count = 1

        aggr_list.append((aggr_date, ((float(aggr_sum) / float(aggr_count)) if doavg else aggr_sum)))

        output.append((el[0], aggr_list))


    return json.dumps(([], output))


@server.route("/api/ubc")
def get_usage_by_character():
    db_output = ubc_db_request(api_state, request)

    return json.dumps(db_output)


@server.route("/api/ubw")
def get_usage_by_word():
    db_conn, db_cursor = getdbconnection()

    words = json.loads(request.args.get("words"))
    mode = param_to_string(request.args.get("mode"))

    if mode == "bydaytime":
        labels = [str(i) + ":00" for i in range(0, 24)]
        return json.dumps((labels, [(word, [el[1] for el in activity_db_pad([i for i in range(0, 24)], ubw_db_request(word, "hour", api_state, request))]) for word in words]))
    elif mode == "byweekday":
        return json.dumps((["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], [(word, [el[1] for el in activity_db_pad([i for i in range(0, 7)], ubw_db_request(word, "weekday", api_state, request))]) for word in words]))
    elif mode == "bytime":
        return json.dumps(([], [(word, [(el[0], el[1]) for el in ubw_db_request(word, "date", api_state, request)]) for word in words]))
    elif mode == "byname":
        names = [el[0] for el in find_names(api_state)]
        return json.dumps((names, [(word, [el[1] for el in activity_db_pad(names, ubw_db_request(word, "name", api_state, request))]) for word in words]))
    elif mode == "total":
        return json.dumps([[word, list(db_cursor.execute("SELECT (SUM(isword) + SUM(isemoji) + SUM(ispunct) + SUM(isuncat)) as usage FROM '{}' WHERE word like ?".format(api_state.table_prefix + '-ubw'), (word, )))[0][0]] for word in words])


@server.route("/api/getoptions")
def get_settings():
    key = param_to_string(request.args.get("key"), None)

    if not key:
        return json.dumps(api_state.settings_global)
    else:
        try:
            return json.dumps(api_state.settings_global[key])
        except KeyError:
            return json.dumps(api_state.settings_global)


@server.route("/api/setoption")
def set_setting():
    key = param_to_string(request.args.get("key"))
    value = param_to_string(request.args.get("value"))

    try:
        api_state.settings_global[key]["selected"] = value
    except KeyError:
        return "Error: no such option"

    try:
        with open(DEFAULT_SETTINGS_FILE, "w") as f:
            f.write(json.dumps(api_state.settings_global))
        return "Success"
    except IOError as e:
        print("[!] Error writing config file!", e)
        return "Error: IOError"


# load and analyze a new file
@server.route("/api/loadnewfile")
def get_loadnewfile():
    filename = request.args.get("filename")

    if not filename:
        return json.dumps((1, "No file specified.", ""))

    return json.dumps(api_state.loadnewfile(filename))


# return list of available, analyzed files
@server.route("/api/getavailfiles")
def get_availfiles():
    db_conn, db_curs = getdbconnection()
    return json.dumps([el[0] for el in list(db_curs.execute("SELECT prefix from chats"))])


# switch between existing files
@server.route("/api/loadfile")
def get_loadfile():
    prefix = request.args.get("prefix")

    if not prefix:
        return "No prefix specified."

    return api_state.loadfile(prefix)


@server.route("/api/getchatssummary")
def get_chatssummary():
    db_conn, db_curs = getdbconnection()
    return json.dumps(list(db_curs.execute("SELECT * FROM chats")))


@server.route("/api/gettotalsummary")
def get_totalsummary():
    db_conn, db_curs = getdbconnection()
    try:
        total_msg = list(db_curs.execute("SELECT SUM(total_msg) FROM chats"))[0][0]
        total_start_date = datetime.datetime.fromisoformat(list(db_curs.execute("SELECT start_date FROM chats ORDER BY start_date LIMIT 1"))[0][0])
        total_end_date = datetime.datetime.fromisoformat(list(db_curs.execute("SELECT end_date FROM chats ORDER BY end_date DESC LIMIT 1"))[0][0])
        total_days = (total_end_date - total_start_date).days
        avg_msg_per_day = total_msg / total_days
        return json.dumps((("Total messages", total_msg), ("Average messages per day", "{:.2f}".format(avg_msg_per_day))))
    except IndexError:
        return json.dumps((("Total messages", 0), ("Average messages per day", 0)))


@server.route("/api/getlang")
def getlang():
    return api_state.lang_global


@server.route("/api/setlang")
def setlang():
    lang = param_to_string(request.args.get("lang"), None)
    dev = param_to_string(request.args.get("dev"), None)
    chat = param_to_string(request.args.get("chat"), None)
    api_state.setlang(lang, dev, chat)

    return "Parser settings successfully set."


@server.route("/api/getresponsetimes")
def getresponsetimes():
    db_conn, db_curs = getdbconnection()

    chats = []
    for chat in db_curs.execute("SELECT prefix FROM chats"):
        chats.append(chat[0])

    data = dict()
    for chat in chats:
        name_last = ""
        dt_last = ""
        data[chat] = dict()
        for line in db_curs.execute("SELECT name, date, time FROM '{}-act'".format(chat)):
            if not name_last:
                name_last = line[0]
            if not dt_last:
                dt_last = line[1] + " " + line[2]
            if not line[0] == name_last:
                dt2 = datetime.datetime.fromisoformat(line[1] + " " + line[2])
                dt1 = datetime.datetime.fromisoformat(dt_last)
                response_time = str(int((dt2 - dt1).seconds / 60))
                if not response_time in data[chat]:
                    data[chat][response_time] = 0
                data[chat][response_time] += 1
            name_last = line[0]
            dt_last = line[1] + " " + line[2]

    return json.dumps(data)


api_state = APIState()

if __name__ == "__main__":
    server.run()
