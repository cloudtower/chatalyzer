import re, os
import json
import datetime
import urllib.parse

from db_utils import getdbconnection

def parse_message_activity(api_state, linerest):
    linesplit = linerest.split(" ")
    inter_punct = []
    inter_emoji = []
    filtered = []

    for word in linesplit:
        hyperlink = re.search(r"https?://[a-zA-Z0-9_!\*'\(\);%@\&=\+\$,/\?\#\[\]\.\~\-]*", word)
        if hyperlink is not None:
            filtered.append(hyperlink.group(0))
        else:
            for part in re.split(r"([^\wäöü]+)", word):
                inter_punct.append(part)

    for word in inter_punct:
        for part in re.split(r"(" + api_state.re_lang_special_chars + r")", word):
            inter_emoji.append(part)

    for word in inter_emoji:
        if re.match(r"[\wäöü]+", word) is None and re.match(api_state.re_lang_special_chars, word) is None:
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
            elif re.match(api_state.re_lang_special_chars, word):
                puncts += 1
            elif len(word) == 1 and isemoji(word):
                emojis += 1
            else:
                words += 1

    return (words, emojis, puncts)

def compute_activity_whatsapp(api_state):
    table_prefix_new = os.path.basename(api_state.fp).split(".")[0]
    table_prefix_new = re.sub(r"\W", "_", table_prefix_new)
    api_state.table_prefix = table_prefix_new
    print("[i] New table prefix: " + api_state.table_prefix)

    print("[i] Computing activity (WhatsApp)...")
    db_conn, db_cursor = getdbconnection()

    db_cursor.execute("CREATE TABLE '{}' (name text, date text, time text, hour integer, weekday integer, ispost integer, ismedia integer, islogmsg integer, words integer, chars integer, emojis integer, puncts integer, message text)".format(api_state.table_prefix + "-act"))

    weekday_last = 0
    hour_last = 0
    day_last = None

    log_msgs = []
    entries = []
    names = []

    name_last = "unknown"

    with open(api_state.fp, encoding="utf-8") as f:
        for line in f:
            try:
                entry = ("unknown", datetime.date(2000, 1, 1), "00:00", 0, 0, 0, 0, 0, 0, 0, 0, 0, "")

                is_message = re.match(api_state.re_lang_filter_syntax, line) is not None
                is_logmsg = re.match(api_state.re_lang_filter_log_syntax, line) is not None
                is_media = re.search(api_state.re_lang_filter_media, line) is not None
                is_cont = False

                if is_message or is_logmsg:
                    if is_message:
                        msg_match = re.match(api_state.re_lang_filter_syntax, line)
                    elif is_logmsg:
                        msg_match = re.match(api_state.re_lang_filter_log_syntax, line)

                    date_time = datetime.datetime.strptime(msg_match.group(1), api_state.lang_datetime)
                    hour_last = date_time.hour
                    time_last = date_time.time().strftime("%H:%M")
                    weekday_last = date_time.weekday()
                    day_last = date_time.date()

                if is_logmsg:
                    log_msgs.append((line, day_last, time_last, hour_last, weekday_last, 0, 0, 1, 0, 0, 0, 0, line))
                else:
                    if is_message:
                        name_last = msg_match.group(3)
                        linerest = line.split(': ', 1)[1]

                        if name_last not in names:
                            names.append(name_last)

                        if is_media:
                            entry = (name_last, day_last, time_last, hour_last, weekday_last, 0, 1, 0, 0, 0, 0, 0, linerest)
                    else:
                        is_cont = True
                        linerest = line

                    if not is_media:
                        words, emojis, puncts = parse_message_activity(api_state, linerest)
                        entry = (name_last, day_last, time_last, hour_last, weekday_last, int(is_message), 0, 0, words, len(linerest), emojis, puncts, linerest)

                    if is_cont:
                        entries[-1] = entries[-1][:8] + (entries[-1][8] + entry[8], entries[-1][9] + entry[9], entries[-1][10] + entry[10], entries[-1][11] + entry[11], entries[-1][12] + entry[12])
                    else:
                        entries.append(entry)
            except Exception as e:
                print("[!] Caught exception during activity computation: " + str(e) + line)

    for element in log_msgs:
        for name in names:
            if name in element[0]:
                entries.append((name, ) + element[1:])

    db_cursor.executemany("INSERT INTO '{}' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(api_state.table_prefix + "-act"), entries)
    db_conn.commit()
    db_conn.close()


def compute_activity_telegram(api_state):
    print("[i] Computing activity (Telegram)...")
    db_conn, db_cursor = getdbconnection()

    with open(api_state.fp, encoding="utf-8") as f:
        data = json.loads(f.read())

    try:
        api_state.table_prefix = data["name"]
    except KeyError:
        api_state.table_prefix = "Saved messages"
    print("[i] New table prefix: " + api_state.table_prefix)
    db_cursor.execute("CREATE TABLE '{}' (name text, date text, time text, hour integer, weekday integer, ispost integer, ismedia integer, islogmsg integer, words integer, chars integer, emojis integer, puncts integer)".format(api_state.table_prefix + "-act"))

    entries = []
    for msg in data["messages"]:
        dt = datetime.datetime.fromisoformat(msg["date"])
        if msg["type"] == "service":
            entries.append(("Telegram", dt.date().isoformat(), dt.time().strftime("%H:%M"), dt.hour, dt.weekday(), 0, 0, 1, 0, 0, 0, 0))
        else:
            if not msg["from"]:
                msg["from"] = "unknown"
            if "file" in msg:
                entries.append((msg["from"], dt.date().isoformat(), dt.time().strftime("%H:%M"), dt.hour, dt.weekday(), 0, 1, 0, 0, 0, 0, 0))
            else:
                if isinstance(msg["text"], list):
                    words, emojis, puncts, chars, msg = 0, 0, 0, 0, ""
                    for el in msg["text"]:
                        if isinstance(el, dict):
                            words += 1
                            chars += len(el["text"])
                            msg += el["text"]
                        else:
                            words_new, emojis_new, puncts_new = parse_message_activity(api_state, el)
                            words += words_new
                            emojis += emojis_new
                            puncts += puncts_new
                            chars += len(el)
                            msg += el
                else:
                    words, emojis, puncts = parse_message_activity(api_state, msg["text"])
                    chars = len(msg["text"])
                    msg = msg["text"]
                entries.append((msg["from"], dt.date().isoformat(), dt.time().strftime("%H:%M"), dt.hour, dt.weekday(), 1, 0, 0, words, chars, emojis, puncts, msg))

    db_cursor.executemany("INSERT INTO '{}' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(api_state.table_prefix + "-act"), entries)
    db_conn.commit()
    db_conn.close()


def parse_message_usage(api_state, linerest, name_last, day_last, hour_last, weekday_last):
    entries = []
    linesplit = linerest.split(" ")
    inter_punct = []
    inter_emoji = []
    filtered = []

    hyperlinks = []
    textemojis = []

    # handle hyperlinks
    for word in linesplit:
        hyperlink = re.search(r"https?://[a-zA-Z0-9_!\*'\(\);%@\&=\+\$,/\?\#\[\]\.\~\-]*", word)
        if hyperlink is not None:
            hyperlinks.append(urllib.parse.urlparse(hyperlink.group(0)).hostname)
            inter_punct.append(word[:hyperlink.span(0)[0]])
            inter_punct.append(word[hyperlink.span(0)[1]:])
        else:
            for part in re.split(r"(" + api_state.re_textemojis + r")", word):
                if part in api_state.textemojis:
                    textemojis.append(part)
                else:
                    for subpart in re.split(r"([^\wäöü]+)", part):
                        inter_punct.append(subpart)

    for word in inter_punct:
        for part in re.split(r"(" + api_state.re_lang_special_chars + r")", word):
            inter_emoji.append(part)

    for i, word in enumerate(inter_emoji):
        # handle keycap emoji sequences
        if i < len(inter_emoji) - 1 and len(inter_emoji[i + 1]) > 0 and ord(inter_emoji[i + 1][0]) == 0x20e3:
            if len(word) > 1:
                filtered.append(word[:-1])
            filtered.append(word[-1] + inter_emoji[i + 1][0])
            inter_emoji[i + 1] = inter_emoji[i + 1][1:]
        else:
            if re.match(r"[\wäöü]+$", word) is None and re.match(api_state.re_lang_special_chars + r"+$", word) is None:
                j = 0
                while j < len(word):
                    toappend = word[j]
                    # handle multiple emojis joined by zero-width space
                    while (j < len(word) - 2 and ord(word[j + 1]) == 0x200d) or (j < len(word) - 2 and ord(word[j + 2]) == 0x200d):
                        if ord(word[j + 1]) == 0x200d:
                            toappend += word[j + 1:j + 3]
                            j += 2
                        else:
                            toappend += word[j + 1:j + 4]
                            j += 3
                            toappend += chr(0xfe0f)
                    # handle emojis with skin color modifier and regional identifiers
                    if j < len(word) - 1 and (isfitzpatrickemoji(word[j + 1]) or isregionalindicator(word[j + 1])):
                        toappend += word[j + 1]
                        j += 1
                    filtered.append(toappend)
                    j += 1
            else:
                filtered.append(word)

    for word in filtered:
        if word != "\n" and word != "":
            if re.match(r'\w+$', word, re.UNICODE):
                entry = (name_last, day_last, hour_last, weekday_last, 1, 0, 0, 0, 0, word.lower())
            elif re.match(api_state.re_lang_special_chars, word):
                entry = (name_last, day_last, hour_last, weekday_last, 0, 0, 1, 0, 0, word)
            elif isemoji(word):
                entry = (name_last, day_last, hour_last, weekday_last, 0, 1, 0, 0, 0, word)
            else:
                entry = (name_last, day_last, hour_last, weekday_last, 0, 0, 0, 0, 1, word)

            entries.append(entry)

    for word in hyperlinks:
        entries.append((name_last, day_last, hour_last, weekday_last, 0, 0, 0, 1, 0, word))
    for word in textemojis:
        entries.append((name_last, day_last, hour_last, weekday_last, 0, 1, 0, 0, 0, word))

    return entries

def compute_usage_whatsapp(api_state):
    print("[i] Computing usage (WhatsApp)...")
    db_conn, db_cursor = getdbconnection()

    db_cursor.execute("CREATE TABLE '{}' (name text, date text, hour integer, weekday integer, isword integer, isemoji integer, ispunct integer, islink integer, isuncat integer, word text)".format(api_state.table_prefix + "-ubw"))

    weekday_last = 0
    hour_last = 0
    day_last = None
    name_last = "unknown"

    entries = []

    with open(api_state.fp, encoding="utf-8") as f:
        for line in f:
            try:
                if re.search(api_state.re_lang_filter_media, line) is None:
                    if re.match(api_state.re_lang_filter_log_syntax, line) is None:
                        if re.match(api_state.re_lang_filter_syntax, line) is not None:
                            msg_match = re.match(api_state.re_lang_filter_syntax, line)
                            date_time = datetime.datetime.strptime(msg_match.group(1), api_state.lang_datetime)
                            hour_last = date_time.hour
                            weekday_last = date_time.weekday()
                            day_last = date_time.date()
                            linerest = line.split(': ', 1)[1]
                            name_last = msg_match.group(3)
                        else:
                            linerest = line

                        entries += parse_message_usage(api_state, linerest, name_last, day_last, hour_last, weekday_last)

            except Exception as e:
                print("[!] Caught exception scanning ubw: " + str(e))

    db_cursor.executemany("INSERT INTO '{}' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(api_state.table_prefix + "-ubw"), entries)
    db_conn.commit()
    db_conn.close()


def compute_usage_telegram(api_state):
    print("[i] Computing usage (Telegram)...")
    db_conn, db_cursor = getdbconnection()

    with open(api_state.fp, encoding="utf-8") as f:
        data = json.loads(f.read())

    db_cursor.execute("CREATE TABLE '{}' (name text, date text, hour integer, weekday integer, isword integer, isemoji integer, ispunct integer, islink integer, isuncat integer, word text)".format(api_state.table_prefix + "-ubw"))

    entries = []
    for msg in data["messages"]:
        dt = datetime.datetime.fromisoformat(msg["date"])
        if msg["type"] == "message":
            if not msg["from"]:
                msg["from"] = "unknown"
            if not "file" in msg:
                if isinstance(msg["text"], list):
                    for el in msg["text"]:
                        if isinstance(el, dict):
                            entries.append((msg["from"], dt.date().isoformat(), dt.hour, dt.weekday(), 0, 0, 0, 1, 0, el["text"]))
                        else:
                            entries += parse_message_usage(api_state, el, msg["from"], dt.date().isoformat(), dt.hour, dt.weekday())
                else:
                    entries += parse_message_usage(api_state, msg["text"], msg["from"], dt.date().isoformat(), dt.hour, dt.weekday())

    db_cursor.executemany("INSERT INTO '{}' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)".format(api_state.table_prefix + "-ubw"), entries)
    db_conn.commit()
    db_conn.close()


def isemoji(ch):
    if len(ch) > 1:
        return all([isemoji(c) for c in ch])

    i = ord(ch)
    return (i in range(0x1f600, 0x1f650) # Emojis
        or i in range(0x1f680, 0x1f700) # Transport and Map Symbols
        or i in range(0x1f300, 0x1f600) # Miscellaneous Symbols and Pictographs
        or i == 0x20e3 # Combining Enclosing Keycap
        or i == 0x200d # Zero Width joiner for multiple Emojis
        or i == 0xfe0f # Variation Selector ending multiple Emojis
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