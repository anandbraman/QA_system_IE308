# Purpose
The code in this repository is a question answering system that uses 2013 and 2014 Business Insider articles to answer the following questions. 

1) Which companies went bankrupt in month X of year Y?
<br><br>
2) What affects GDP? After this question, the user is asked if they would like to ask a follow-up. If the answer is "Yes", then the user is prompted to ask a question of the following format: *What percentage of drop or increase is associated with X?* The user can ask as many follow-ups of this format as they want. Afterward, the user can ask other questions, if they would like. 
<br><br>
3) Who is the CEO of company X?
<br>
After asking questions the user is free to keep asking questions or enter "No further questions." when they are finished. 

# Running the Code
### Software Requirements
To run this code you must have ElasticSearch downloaded. Follow the instructions here: https://www.elastic.co/downloads/elasticsearch
<br>
Following the download instructions should lead you to an ElasticSearch cluster running locally on your machine. After this, the user should be able to run `qa_system.py` from the command line. 
