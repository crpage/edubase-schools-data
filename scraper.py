"""
Obtains the edubase schools database

http://www.edubase.gov.uk
"""

from scraperwiki import sqlite, scrape
from lxml import html
import mechanize
import re
import time


def main():
    urns = shallow_scrape()
    
    for urn in urns:
        print "  URN: " + urn
        deep_scrape(urn)


def shallow_scrape():
    br = mechanize.Browser()

    c = sqlite.get_var('last_page', 0) + 1
    max_c = c + 100
    
    resultspage = br.open("http://www.education.gov.uk/edubase/quickSearchResult.xhtml?page=%d" % c)

    while c < max_c:
        print "Handling page %d..." % c
        print "  [" + br.geturl() + "]"
    
        ### extract data from page
        page = html.parse(resultspage)

        for u in page.getroot().findall("body/div/div/div/div/table/tr/td/table/tbody/tr/td/a"):
            urn = re.search("urn=([0-9]{6})", u.get("href")).group(1)
            yield urn

        ### get new page
        try:
            resultspage = br.follow_link(text="Next")
            c += 1
            if c % 2 == 0:
                time.sleep(10)
                
        except mechanize.LinkNotFoundError:
            c = 1
            break
    
    sqlite.save_var('last_page', c - 1)

keys_to_keep = [
'Local Authority', 'Type of Establishment', 'Locality', 'Establishment Number', 'School Capacity', 'Statutory Lowest Pupil Age', 
'Status', 'Website Address',  'Town', 'Telephone Number', 'Gender', 'URN', 
'Northing', 'Total Number of Children', 'Urban / Rural', 'Age Range', 'Establishment Type Group', 'Phase of Education', 
'Headteacher', 'Statutory Highest Pupil Age', 'County', 'Street', 'Postcode', 'Easting', 'Establishment Name', 'Address 3'
]

def deep_scrape(urn):
    data = {}

    def merge_in(d):
        "update data with d; complain if anything is overwritten"
        for (k,v) in d.iteritems():
            if k in data:
                assert data[k] == v, "%s: [%s] != [%s]" % (k, data[k], v)
            else:
                data[k] = v

    merge_in(summary_scrape(urn))
    merge_in(page_scrape('general', urn))
    merge_in(page_scrape('communications', urn))
    merge_in(page_scrape('regional-indicators', urn))
    
    try:
        if "Headteacher" not in data:
            data["Headteacher"] = "".join([
                data["Headteacher Title"],
                data["Headteacher First Name"],
                data["Headteacher Last Name"]
            ])
        
        if data["Easting"] == "" or data["Northing"] == "":
            raise Exception("No Location Data")

        data = { key: data[key] for key in keys_to_keep }
    
        sqlite.save(unique_keys=["URN"], data=data)
    
    except Exception as e:
        print "Error: " + e.message
    #return data


def summary_scrape(urn):
    url = "http://www.education.gov.uk/edubase/establishment/summary.xhtml?urn=" + urn
    page = html.fromstring(scrape(url))

    data = table_extract(page)

    for t in page.findall("body/div/div/div/div/table/tr/td/h1"):
        key, value = t.text.split(": ", 1)
        data[key] = value

    for t in page.findall("body/div/div/div/div/table/tr/td/div/p/b"):
        data[t.text.strip().strip(":")] = (t.tail or "").strip()

    return data


def page_scrape(name, urn):
    url = "http://www.education.gov.uk/edubase/establishment/"+name+".xhtml"+"?urn="+urn
    page = html.fromstring(scrape(url))
    return table_extract(page)

def table_extract(page):
    data = {}
    
    for tr in page.findall("body/div/div/div/div/table/tr/td/" + "div/table//tr"):
        for a, b in ((1,1), (2,3)):
            th = tr.find("th[%s]" % a)
            td = tr.find("td[%s]" % b)

            key = (th.text or "") if th is not None else ""
            value = (td.text or "") if td is not None else ""

            if key in data:
                data[key] = data[key] + " / " + value
            else:
                data[key] = value
    
    if "" in data:
        del data[""]

    return data

if __name__ == "__main__":
    main()
    
