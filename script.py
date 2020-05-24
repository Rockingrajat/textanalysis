import requests
# Import BeautifulSoup
from bs4 import BeautifulSoup
# import re module for REGEXes
import re
import os
import pandas as pd

def parse(file1, file2):
	with open(file1,'r') as hand: 
     
		IDENTITY=""
		for line in hand:
		    #print(line)
		    line=line.strip()
		    if re.findall('^CONFORMED SUBMISSION TYPE:',line):
		        k = line.find(':')
		        subtype=line[k+1:]
		        subtype=subtype.strip()
		        #print subtype
		        IDENTITY=IDENTITY+'FORM TYPE: '+str(subtype)+'\n'
		        break
		        

		for line in hand:
			#print(line)
			line=line.strip()
			if re.findall('^CONFORMED PERIOD OF REPORT:',line):
				k = line.find(':')
				cper=line[k+1:]
				cper=cper.strip()
				IDENTITY=IDENTITY+'REPORT PERIOD END DATE: '+str(cper)+'\n'
				break
		        

		for line in hand:
		    line=line.strip()
		    if re.findall('^FILED AS OF DATE:',line):
		        k = line.find(':')
		        fdate=line[k+1:]
		        fdate=fdate.strip()
		        #print fdate                                
		        IDENTITY=IDENTITY+'FILE DATE: '+str(fdate)+'\n'
		        break
		for line in hand:
		    line=line.strip()
		    if re.findall('^COMPANY CONFORMED NAME:',line):
		        k = line.find(':')
		        comnam=line[k+1:]
		        comnam=comnam.strip()
		        IDENTITY=IDENTITY+'COMPANY NAME: '+str(comnam)+'\n'                                         
		        break
		    

		for line in hand:
		    line=line.strip()
		    if re.findall('^CENTRAL INDEX KEY:',line):
		        k = line.find(':')
		        cik=line[k+1:]
		        cik=cik.strip()
		        #print cik
		        IDENTITY=IDENTITY+'CIK: '+str(cik)+'\n'
		        break
		    

		for line in hand:
		    line=line.strip()
		    if re.findall('^STANDARD INDUSTRIAL CLASSIFICATION:',line):
		        k = line.find(':')
		        sic=line[k+1:]
		        sic=sic.strip()
		        siccode=[]
		        for s in sic: 
		            if s.isdigit():
		                siccode.append(s)    
		        #print siccode
		        IDENTITY=IDENTITY+'SIC: '+''.join(siccode)+'\n'
		        break
		
	
	with open(file2, 'w') as f:
	    f.write(str(IDENTITY))
	    f.close()


def get_risk_factors(raw_10k, file):
	doc_start_pattern = re.compile(r'<DOCUMENT>')
	doc_end_pattern = re.compile(r'</DOCUMENT>')
	# Regex to find <TYPE> tag prceeding any characters, terminating at new line
	type_pattern = re.compile(r'<TYPE>[^\n]+')

	doc_start_is = [x.end() for x in doc_start_pattern.finditer(raw_10k)]
	doc_end_is = [x.start() for x in doc_end_pattern.finditer(raw_10k)]

	### Type filter is interesting, it looks for <TYPE> with Not flag as new line, ie terminare there, with + sign
	### to look for any char afterwards until new line \n. This will give us <TYPE> followed Section Name like '10-K'
	### Once we have have this, it returns String Array, below line will with find content after <TYPE> ie, '10-K' 
	### as section names
	doc_types = [x[len('<TYPE>'):] for x in type_pattern.findall(raw_10k)]


	document = {}

	# Create a loop to go through each section type and save only the 10-K section in the dictionary
	for doc_type, doc_start, doc_end in zip(doc_types, doc_start_is, doc_end_is):
	    if doc_type == '10-K':
	    	document[doc_type] = raw_10k[doc_start:doc_end]
			
			


	regex = re.compile(r'(>Item(\s|&#160;|&nbsp;)(1A|1B|2)\.{0,1})|(ITEM\s(1A|1B|2))')

	# Use finditer to math the regex
	matches = regex.finditer(document['10-K'])

	# Create the dataframe
	test_df = pd.DataFrame([(x.group(), x.start(), x.end()) for x in matches])

	test_df.columns = ['item', 'start', 'end']
	test_df['item'] = test_df.item.str.lower()

	test_df.replace('&#160;',' ',regex=True,inplace=True)
	test_df.replace('&nbsp;',' ',regex=True,inplace=True)
	test_df.replace(' ','',regex=True,inplace=True)
	test_df.replace('\\.','',regex=True,inplace=True)
	test_df.replace("\t"," ",regex=True,inplace=True)
	test_df.replace("\v","",regex=True,inplace=True)
	test_df.replace('\\s+'," ",regex= True,inplace = True)  
	test_df.replace('>','',regex=True,inplace=True)

	pos_dat = test_df.sort_values('start', ascending=True).drop_duplicates(subset=['item'], keep='last')

	pos_dat.set_index('item', inplace=True)
	item_1a_raw = document['10-K'][pos_dat['start'].iloc[0]:pos_dat['start'].iloc[1]]
	item_1a_content = BeautifulSoup(item_1a_raw, 'lxml')
	item_1a_content =  item_1a_content.get_text('\n').strip()
	cleaned_risk_factor = item_1a_content.split('\n')
	num = re.compile(r'[0-9]')
	filter_obj = filter(lambda x: x.strip() != "" , cleaned_risk_factor)#cleaned_risk_factor = [cleaned_risk_factor if cleaned_risk_factor not ""]
	filter_2 = filter(lambda x:not num.match(x),list(filter_obj))
	filter_2 = [x.strip() for x in filter_2]

	with open(file,'a') as f:
		f.write("\n".join(list(filter_2)))
		f.close()
	

file = pd.read_excel('downloadlist_htm.xlsx')
num_files = 1
for row in file['pretext_iname'].head(num_files):
			download_link = row.replace('-index.htm','.txt')
			file_name = download_link.split('/')[-1]

			if not os.path.exists(download_link.split('/')[-1]):
				os.system('wget '+download_link)
				print('Downloading file '+file_name)
			else:
				print('File '+file_name+" already downloaded")
			
			r = requests.get(download_link)
			raw_10k = r.text
			
			clean_file_name = file_name.split('.')[0]+"_cleaned.txt"
			if os.path.exists(clean_file_name):
				print("Skipping file: "+file_name+", cleaned file "+clean_file_name+" already exists!")
			else:
				print('Creating file '+clean_file_name)
				parse(file_name,clean_file_name)
				get_risk_factors(raw_10k,clean_file_name)
			# from requests_html import HTML
			# html=HTML(html=raw_10k)
			# print(html.text)