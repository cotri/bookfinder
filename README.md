# bookfinder

`bookfinder` is a script that, given an _Excel_ file which contains a formatted list of books (see [book_list.ods][1]), it searches, compares prices and generates a secondary/output CSV file named _temporal_ where the books and their resulting prices from the scrapping are sorted and displayed.

It is based on the book meta-search webpage [BookFinder][2] to obtain the prices (supposed cheaper) that will be compared against the provided _reference_ prices in the _Excel_ file.

The following README gives an explanation of the usage, files handled by bookfinder and addresses some questions regarding how the script works.

## Introduction

So, a couple of years ago discovered reading and proceeded to track down, purchase (if affordable) and binge all the books I could. This script is just the result of some sort of rush for getting the _best deals_ and a way to loose time under the pretext of _automatization_ (overspending money and time? Anyone?).

## Dependencies

- `python3`
- `time`
- `pandas`
- `urllib`
- `Selenium`
- `fake_useragent`
- Firefox browser driver `geckodriver`

## Usage

The whole script has been commented more than I am comfortable with for the sake of better understanding for someone new to it.

Together with these comments there are some fields that **must** be filled/modified before anything else to suit each individual needs such as:

- Path to files
- Country and currency
- Decimal separator

These are denoted with a `# TODO:` in the code.

The automated web scrapping is done with `Selenium`. The script uses Firefox's web driver[^1] (required to run `Selenium`) called _geckodriver_ which will need to be downloaded from [Mozilla's GitHub][3].

[^1]: Other drivers, such as ChromeDrive, can be used, though. You will need to search how.

The script by default will run `Selenium` with Firefox in a non-headless mode. However, it is possible to uncomment the corresponding line of code to make the browser run in headless mode (see [here][4]).

Once everything is set up, make the script executable and run it from the terminal:
```bash
chmod u+x bookfinder.py   # Equivalent of 744
python bookfinder.py
```

Better yet, a wrapper shell script can be written that lets you know when the script has finished with a nice notification. However, understand that the following example is tailored to my system, you may need some extra dependencies or different config settings. Feel free to adapt it to yours if you choose so.
```bash
#!/bin/sh

bell="path/to/sounds/complete.oga"
book_list="path/to/temp_book_list.csv"

# Actual script
bookfinder.py

# Notification
paplay "$bell" &
action=$(dunstify \
            --action="view,view" \
            --urgency=low \
            --timeout=0 \
            --hints=string:x-dunst-stack-tag:bookfinder \
            --appname=bookfinder \
            "<NOTIFICATION TITLE>" \
            "<NOTIFICATION BODY>")

case "$action" in
    view)
        xdg-open "$book_list" ;;
    *)
        exit 1 ;;
esac

```

### Input file: _Excel book_list_

File named _'book_list'_ (by default _.ods_, but it can be _.xlsx_ [^2]) formatted as indicated in the example template [book_list.ods][1]. The template is structured in such way that the field names (the ones from the table header, eg: _ISBN_, _AMZN_) **must** coincide with the field names the script is going to use. Otherwise it will not work.

This file is _static_, in the sense that the script only reads from it and imports the books as a dataframe. It consists of a table with:
    
- Reference prices, manually taken from Amazon (_AMZN_)
- Found prices manually introduced after scrapping from [BookFinder][2] (_BookFndr_)
- Basic information to identify the book (_ISBN_, _Author_ and _Title_)
- Some minor calculations (_Price diff_ and _Percentage_)

[^2]: To import an XLSX file instead, remove the `engine='odf'` from [here][5].

### Output file: _Temporal CSV temp_book_list_

Temporal CSV file named _'temp_book_list.csv'_ created by the script. It is generated line by line as it iterates, scraps and appends each book entry one by one. Referred to as _temporal_ because each time the script is run it overwrites the previous file.

This output file displays the books listed in [book_list.ods][1] with their present _BookFndr_ prices obtained from the current run. The following new fields are introduced:

- _% increase_: difference of percentages between the current _Percentage_ and the _Percentage_ calculated in [book_list.ods][1]
- _NH: New High._ Shows if a new cheaper price is found in the current scrapping

The books are sorted so that:

- First, the books whose prices from the current scrapping are lower than the ones from the _previous scrapping_ (_BookFndr_ prices present in [book_list.ods][1]) are shown. These are distinguished for having the _NH_ field set to _True_
- Then, the books that even though are not categorized as _NH_ but meet any of the other price conditions (see [here][6]). For example, books that are heavily discounted $(\geq{40}\\%)$ or with _cheap_ prices $(\leq{\$10})$. These have _NH_ set to _False_
- Lastly, the books that do not meet any of the previous conditions. These do not have _NH_ set, it is empty

Inside each category (_NH_: _True_, _False_, _''_), the books are sorted by _Percentage_ from most discounted to less discounted (descending) and, finally, from lower to higher _BookFndr_ price (ascending).

As a sidenote, it is a little bit contradicting the fact that I am referring to the books whose prices are lower after the scrapping as _New Highs_ when, in fact, they should be _New Lows_. At the time I just found more appealing _High_ (as in higher discount) than _Low_ which may have _negative connotations_ in other cases (specially if you are invested in the crypto market).

## FAQ

### Wait, but where do I get all the Amazon and BookFinder prices if it is my first run?

At the time of writing, sadly, all the data stored in [book_list.ods][1] is manually added/modified.

It all started with an _Excel_ named _book_list_ where I manually added, searched and updated prices. The script all it does is to automate the searching and price comparison part, outputting another temporal file with the current prices updated for that run.

So, any new books and prices that you want the script to account for **must** be manually introduced in [book_list.ods][1].

### What is the Bear Book thing about?

Apparently, there is an Amazon seller by the name of _Bear Book Sales_ to which [BookFinder][2] applies certain shipping taxes. When in fact, at least in my case, the shipping is free.

Thus, the script looks for _Bear Book_ and, if so, deducts the shipping from the total price and checks if this new price is lower than the current one.

### What you are doing with `Selenium` couldn't it be done much simpler with `requests`?

Yes and no. I am not able to point to the specific causes that make `requests` unreliable to scrap [BookFinder][2], but when using `requests.get()` to obtain the HTML code there are some books for which the webpage loads correctly and some others for which the response HTML content is empty.

My suspicion lies on the fact that the webpage may need to load some JavaScript or cookies which, contrary to `Selenium`, `requests` is not able to handle properly. (No idea what I'm talking about TBH)

### Addressing the reference price bias

The script uses the reference price, _AMZN_, as comparison to the scrapped price, _BookFndr_, to obtain the various metrics that, in turn, dictate how the books are sorted in the output file. And how are the books _perceived_ by the end user as cheapest/priciest or more/less discounted.

I believe this reference price from Amazon certainly is far from suitable to make a meaningful comparison because:

- Mainly, you are comparing new books (from Amazon) to second hand books
- Books that arrive in the next day or next few days compared to books which may take much longer depending on where the seller is located
- Books that most of the time come well packaged with books that have made it in little more than a plastic film and a sticker as packaging


[1]: book_list.ods
[2]: https://www.bookfinder.com
[3]: https://github.com/mozilla/geckodriver/releases
[4]: bookfinder.py#L92
[5]: bookfinder.py#L125
[6]: bookfinder.py#L238-L241
