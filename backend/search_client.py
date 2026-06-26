from ddgs import DDGS

BAD_SNIPPET_HINTS=[
    "saudi arabia",
    "dubai",
    "abu dhabi",
    "riyadh",
]

SOCIAL_DOMAINS=[
    "instagram.com",
    "tiktok.com",
    "facebook.com",
]

OFFICIAL_OR_USEFUL_DOMAINS=[
    "visitqatar.com",
    "educationcity.qa",
    "qf.org.qa",
    "hbku.edu.qa",
    "qatarrail.qa",
    "mowasalat.com",
    "msheireb.com",
    "mdd.com.qa",
]


def _is_local_query(query):
    q=query.lower()
    return any(word in q for word in ["qatar","doha","msheireb","education city","qcri","minaretein"])


def _is_local_recommendation_query(query):
    q=query.lower()
    return _is_local_query(q) and any(word in q for word in ["cafe","coffee","qahwa","karak","dates","restaurant","spot"])


def web_search(query,num_results=5):
    results=[]
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query,max_results=num_results+8):
                title=item.get("title","")
                link=item.get("href","")
                snippet=item.get("body","")
                joined=f"{title} {link} {snippet}".lower()

                # Avoid neighbour-country poison for Qatar-local recs.
                if _is_local_query(query):
                    if any(hint in joined for hint in BAD_SNIPPET_HINTS) and "qatar" not in joined and "doha" not in joined:
                        continue

                # Social video hits are weak evidence for local recommendations.
                # They can be useful for hype, but they should not steer a demo answer.
                if _is_local_recommendation_query(query):
                    if any(domain in joined for domain in SOCIAL_DOMAINS):
                        continue

                results.append({"title":title,"link":link,"snippet":snippet})
                if len(results)>=num_results:
                    break
    except Exception as e:
        print("Search failed:",e)
        return []
    return results


if __name__=="__main__":
    results=web_search("qahwa dates cafe near Msheireb Doha")
    print("Results found:",len(results))
    for result in results:
        print("\nTITLE:",result["title"])
        print("LINK:",result["link"])
        print("SNIPPET:",result["snippet"])
