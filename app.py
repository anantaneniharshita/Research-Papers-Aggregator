import os
import json
from flask import Flask, request, jsonify, render_template
import requests
from bs4 import BeautifulSoup
import time

app = Flask(__name__)
JSON_FILE_PATH = "papers_index.json"

# PubMed Crawler
def crawl_pubmed(keyword, max_results=10):
    base_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={keyword}&retmax={max_results}&retmode=xml"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'xml')
    id_list = [id_tag.text for id_tag in soup.find_all('Id')]

    papers = {}
    for pmid in id_list:
        paper_details_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=xml"
        details_response = requests.get(paper_details_url)
        details_soup = BeautifulSoup(details_response.content, 'xml')
        entry = details_soup.find('DocSum')
        if entry:
            title = entry.find('Item', {'Name': 'Title'})
            doi = entry.find('Item', {'Name': 'DOI'})
            paper_id = f"PubMed_{pmid}"
            papers[paper_id] = {
                'title': title.text.strip() if title else 'No title available',
                'url': f"https://doi.org/{doi.text}" if doi else 'No DOI available',
                'summary': 'not found',
                'source': 'PubMed'
            }
    return papers

# Arxiv Crawler
def crawl_arxiv(keyword, max_results=25):
    base_url = f"http://export.arxiv.org/api/query?search_query=all:{keyword}&start=0&max_results={max_results}"
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'lxml-xml')
    entries = soup.find_all('entry')

    papers = {}
    for entry in entries:
        arxiv_id = entry.id.text.split('/')[-1]
        paper_id = f"arXiv_{arxiv_id}"
        papers[paper_id] = {
            'title': entry.title.text.strip(),
            'url': entry.id.text.strip(),
            'summary': entry.summary.text.strip() if entry.summary else "no summary",
            'source': 'arXiv'
        }
    return papers

# Save papers to JSON
def save_to_json(data):
    # if os.path.exists(JSON_FILE_PATH):
    #     with open(JSON_FILE_PATH, "r") as file:
    #         existing_data = json.load(file)
    # else:
    #     existing_data = {}
    existing_data = {}
    # Merge new data into existing data
    existing_data.update(data)

    with open(JSON_FILE_PATH, "w") as file:
        json.dump(existing_data, file, indent=4)

# Load papers from JSON
def load_from_json():
    if os.path.exists(JSON_FILE_PATH):
        with open(JSON_FILE_PATH, "r") as file:
            return json.load(file)
    return {}

# Home Page Route
@app.route('/')
def home():
    return render_template('topics.html')

# Trigger paper fetching when a topic is selected
@app.route('/fetch_papers')
def fetch_papers():
    topic = request.args.get('topic', '')
    if not topic:
        return jsonify({"error": "No topic provided"}), 400

    # Crawl papers from PubMed and arXiv
    pubmed_papers = crawl_pubmed(topic)
    
    # for paper_id, paper_details in pubmed_papers.items():
    #     print(f"Title: {paper_details['title']}")
    #     print(f"URL: {paper_details['url']}")
    #     print(f"Source: {paper_details['source']}")
    #     print("------")
  
    arxiv_papers = crawl_arxiv(topic)

    # Merge both PubMed and arXiv papers
    all_papers = arxiv_papers.copy()  # Create a copy to avoid modifying the original pubmed_papers
    all_papers.update(pubmed_papers)
    for paper_id, paper_details in all_papers.items():
        print(f"Title: {paper_details['title']}")
        print(f"URL: {paper_details['url']}")
        print(f"Source: {paper_details['source']}")
        print("------")
    # Save the merged papers to the JSON file
    save_to_json(all_papers)
    
    
    return jsonify({"message": "Crawling complete, papers saved to JSON."})

# Fetch papers from JSON for the selected topic
@app.route('/fetch_papers_from_json')
def fetch_papers_from_json():
    topic = request.args.get('topic', '')
    papers = load_from_json()

    # Filter papers based on the topic (case-insensitive)
    filtered_papers = [
    paper for paper in papers.values()
    if topic.lower() in paper['title'].lower() or topic.lower() in paper['summary'].lower()
]
    
    return jsonify(filtered_papers)

# Results Page Route
@app.route('/results')
def results():
    return render_template('results.html')

if __name__ == '__main__':
    app.run(debug=True)
