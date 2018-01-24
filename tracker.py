import requests
import csv
import json
from bs4 import BeautifulSoup
from matplotlib import pyplot as plt

# This is the new version of bs1
# Use lxml
# * label first, last, highest and lowest data point
# create DATA object
# # ---build alerts
# add today's appreciation to final graph set

data = {}


def marshall(data):
    with open("fun_data.json") as json_file:
        data = json.load(json_file)

    # text = input("Add a new fund to track or press enter to continue: ")
    # if text:
    #     data[text] = {}
    return (data)


# returns a list of etf keys with owned funds first
def symbol_list(data):
    symbols = []
    for symbol in data:
        if len(symbols) == 0:
            symbols.append(symbol)
        elif data[symbol]["holdings"]["shares"] == "0":
            symbols.append(symbol)
        else:
            symbols.insert(0, symbol)
    return symbols


def get_prices(data, records=10):
    for symbol in data:
        q = requests.get("https://www.barchart.com/proxies/timeseries/queryeod.ashx?symbol="+symbol+"&funds_dict=daily&maxrecords="+str(records)+"&volume=contract&order=asc&dividends=false&backadjust=false&daystoexpiration=1&contractroll=expiration")
        d = q.content.decode('utf-8')
        cr = csv.reader(d.splitlines(), delimiter=',')
        rows = list(cr)
        if len(rows) > 10:
            if not rows[8][1] in data[symbol].keys():
                data[symbol][rows[8][1]] = {}
            data[symbol][rows[8][1]]["price"] = rows[8][5]
            if not rows[9][1] in data[symbol].keys():
                data[symbol][rows[9][1]] = {}
            data[symbol][rows[9][1]]["price"] = rows[9][5]
            data[symbol]["today"] = rows[9][1]
            data[symbol]["price"] = rows[9][5]
    return data


def get_opinion(data):
    for symbol in data:
        url = "https://www.barchart.com/etfs-funds/quotes/"+symbol+"/opinion"
        result = requests.get(url)
        soup = BeautifulSoup(result.text, "html.parser")
        if (data[symbol]["name"] == ""):
            fund = soup.find("div", class_="symbol-name").text
            data[symbol]["name"] = fund
        opinion = soup.find("span", class_="opinion-percent").text
        signal = soup.find("span", class_="opinion-signal").text
        if signal == "Hold":
            data[symbol][data[symbol]["today"]]["opinion"] = 0
        elif signal == "Sell":
            data[symbol][data[symbol]["today"]]["opinion"] = (-1)*float(opinion.strip('%'))
        else:
            data[symbol][data[symbol]["today"]]["opinion"] = float(opinion.strip('%'))
    return data


# accounts for the purchase not happening at EOD by changing the EOD price
def adjust_data(data, symbols):
    for symbol in symbols:
        if "date" in data[symbol]["holdings"].keys():
            doi = data[symbol]["holdings"]["date"]
            poi = data[symbol]["holdings"]["cost basis"]
            data[symbol][doi]["price"] = poi
    return data


def list_of_days(symbol, purchase_date=0):
    if "date" in symbol["holdings"].keys():
        purchase_date = symbol["holdings"]["date"]
    x = list(symbol.keys())
    if "name" in x:
        x.remove("name")
    if "holdings" in x:
        x.remove("holdings")
    if "today" in x:
        x.remove("today")
    if "price" in x:
        x.remove("price")
    x.sort()
    if purchase_date != 0:
        start = x.index(purchase_date)
    else:
        start = len(x) - 15
    return x[start:]


def build_opinion_list(symbol, days):
    op = []
    for day in days:
        if "opinion" in symbol[day]:
            op.append(round(float(symbol[day]["opinion"]/10), 2))
        else:
            op.append(0)
    return op


def build_change_list(symbol, days):
    ch = []
    day_before = 0
    for day in days:
        change = 0
        if "price" in symbol[day].keys():
            price = float(symbol[day]["price"])
            if (day_before != 0 and "price" in symbol[day_before].keys()):
                delta = price - float(symbol[day_before]["price"])
                change = round((100 * delta / (price - delta)), 2)
            elif "today's_change" in symbol[day]:
                change = (round(float(symbol[day]["today's_change"]), 2))
        day_before = day
        ch.append(change)
    return ch


def build_header_data(data, symbols):
    headers = {}
    for symbol in symbols:
        days = list_of_days(data[symbol])
        headers[symbol] = {}
        current_value = float(data[symbol][days[-1]]["price"]) * float(data[symbol]["holdings"]["shares"])
        appreciation_today = (float(data[symbol][days[-1]]["price"]) - float(data[symbol][days[-2]]["price"])) * float(data[symbol]["holdings"]["shares"])
        headers[symbol]["current_value"] = current_value
        headers[symbol]["appreciation_today"] = appreciation_today
    return headers


def build_returns_list(symbol, days):
    re = []
    for day in days:
        re.append((float(symbol[day]["price"]) - float(symbol["holdings"]["cost basis"])) / float(symbol["holdings"]["cost basis"]) * 100)
    return re


# we are including stuff that hasn't been bought yet and not including cash no hand. buy sell and cash functionality needs to come eventually...
def build_total_value_list(data, days):
    va = []
    # mutual funds won't be included in the final number until after market close. To be reasonably representative, we save the previous day's value for that calculation
    funds = {}
    for day in days:
        tv = 0
        for symbol in symbols:
            if day in data[symbol].keys():
                tv += float(data[symbol][day]["price"])*float(data[symbol]["holdings"]["shares"])
                if not symbol in funds.keys():
                    funds[symbol] = {}
                funds[symbol]["price"] = data[symbol][day]["price"]
            elif symbol in funds.keys():
                tv += float(funds[symbol]["price"])*float(data[symbol]["holdings"]["shares"])
        va.append(tv)
    return va


def ddp(data_set, fund, headers):

    fig, ax = plt.subplots()
    (x, d, y, c, r) = zip(*data_set)

    ax.plot(x, c, label="today's % change")
    ax.plot(x, r, label="% roi")
    pairs = list(zip(x, y))
    while pairs[0][1] == 0:
        del pairs[0]
    (x, y) = zip(*tuple(pairs))
    ax.plot(x, y, label="opinion")
    # oz = [0]*len(x)
    ax.plot(x, [0]*len(x))
    h = max(y)

    # these data point text labels are actually completely independent of the points
    text_set = data_set[0:-1:(int(len(data_set)/5))]
    if text_set[-1] != data_set[-1]:
        text_set = list(text_set)
        text_set.append(data_set[-1])

    for i in range(len(text_set)):
        (x, d, y, c, r) = text_set[i]
        (dd, dl, tr, dr, dp) = (0, 10, 0, 90, 10)
        i = 0
        for v in [y, c, r]:
            if v < (h / 2):
                dd = 1
            if i == 1:
                dl = 0
            if i == 2:
                dl = 20
            i += 1
            #don't print 0's
            if v != 0:
                t = ax.text(x, v, str(round(v, 2)), withdash=True,
                            dashdirection=dd,
                            dashlength=dl,
                            rotation=tr,
                            dashrotation=dr,
                            dashpush=dp,
                            )

    # override the default x axis labels
    (ex, de, wy, ch, re) = zip(*text_set)
    plt.xticks(ex, de)
    plt.subplots_adjust(bottom=0.15, top=0.85) # default top is 0.9
    for label in ax.get_xticklabels():
        label.set_rotation(270)

    # add header box
    if not headers["current_value"] == 0.0:
        fc = 'xkcd:sky blue'
        if headers["appreciation_today"] < 1:
            fc = 'red'
        print("headers['current_value']", headers["current_value"])
        box_text = "Current Value: " + "$" + str(round(headers["current_value"], 0)) + " " + "Today's Appreciation: " + "$" + str(round(headers["appreciation_today"], 0))
        plt.text(0.5, 1.15, box_text,
                 horizontalalignment='center',
                 verticalalignment='center',
                 style='italic',
                 transform=ax.transAxes,
                 bbox={'facecolor': fc, 'alpha': .5, 'pad': 3})

    plt.legend()
    plt.title(fund)
    plt.show()


def ddp1(data_set, title):
    fig, ax = plt.subplots()
    (x, d, y) = zip(*data_set)
    ax.plot(x, y, label="opinion")
    h = max(y)

    # these data point text labels are actually completely independent of the points
    text_set = data_set[0:-1:(int(len(data_set)/5))]
    if text_set[-1] != data_set[-1]:
        text_set = list(text_set)
        text_set.append(data_set[-1])

    for i in range(len(text_set)):
        (x, d, y) = text_set[i]
        (dd, dl, tr, dr, dp) = (0, 10, 0, 90, 10)
        for v in [y]:
            if v < (h / 2):
                dd = 1
            #don't print 0's
            if v != 0:
                t = ax.text(x, v, str(round(v, 2)), withdash=True,
                            dashdirection=dd,
                            dashlength=dl,
                            rotation=tr,
                            dashrotation=dr,
                            dashpush=dp,
                            )
    # override the default x axis labels
    (ex, de, wy) = zip(*text_set)
    plt.xticks(ex, de)
    plt.subplots_adjust(bottom=0.2)
    for label in ax.get_xticklabels():
        label.set_rotation(270)



    plt.legend()
    plt.title(title)
    plt.show()


def plot_opinion_change_return(data, headers):
    for symbol in symbols:
        days = list_of_days(data[symbol])
        op = build_opinion_list(data[symbol], days)
        ch = build_change_list(data[symbol], days)
        re = build_returns_list(data[symbol], days)
        days = [str(int(day.replace('-', '')) - 20000000) for day in days]
        exes, days = zip(*[day for day in enumerate(days)])
        data_set = tuple(zip(exes, days, op, ch, re))
        ddp(data_set, symbol, headers[symbol]) #header[symbol]


def plot_total_value(data):
    days = list_of_days(data[symbols[-1]], "2017-12-29")
    va = build_total_value_list(data, days)
    days = [str(int(day.replace('-', '')) - 20000000) for day in days]
    exes, days = zip(*[day for day in enumerate(days)])
    data_set = tuple(zip(exes, days, va))
    ddp1(data_set, "Total Value")
    return (va, days, exes)


def plot_profit(va, days, exes):
    gr = [v - va[0] for v in va]
    data_set = tuple(zip(exes, days, gr))
    ddp1(data_set, "Profit")


def report_totals():
    for symbol in symbols:
        days = list_of_days(data[symbol])
        day = days[-1]
        fidelity = 0
        if day in data[symbol].keys():
            tv = float(data[symbol][day]["price"])*float(data[symbol]["holdings"]["shares"])
            print(symbol, day, " total_value ", tv)
        else:
            tv = float(data[symbol][days[-2]]["price"])*float(data[symbol]["holdings"]["shares"])
            print(symbol, days[-2], " total_value ", tv)
        if tv > 0 and symbol != 'VTSAX':
            fidelity += tv
    print("fidelity ", day, " total_value ", fidelity)


# main
data = marshall(data)
symbols = symbol_list(data)
data = get_prices(data)
data = get_opinion(data)
with open("fun_data.json", "w") as writeJSON:
    json.dump(data, writeJSON)
headers = build_header_data(data, symbols)
data = adjust_data(data, symbols)
plot_opinion_change_return(data, headers)
(va, days, exes) = plot_total_value(data)
plot_profit(va, days, exes)
report_totals()


