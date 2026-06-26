from ddgs import DDGS

BAD_SNIPPET_HINTS=[
    "saudi arabia","dubai","abu dhabi","riyadh","charleston","south carolina",
    "girls' getaway","girls getaway","new york","london","miami","bahrain","kuwait",
]

SOCIAL_DOMAINS=["instagram.com","tiktok.com","facebook.com"]

OFFICIAL_OR_USEFUL_DOMAINS=[
    "visitqatar.com","educationcity.qa","qf.org.qa","hbku.edu.qa","qatarrail.qa",
    "mowasalat.com","msheireb.com","mdd.com.qa","dohahamadairport.com",
]

LOCAL_SCOPE_WORDS=[
    "qatar","doha","msheireb","education city","qcri","minaretein","lusail",
    "wakra","al wakra","mansoura","west bay","the pearl","souq waqif","hia",
    "hamad international","qatar rail","banana island","anantara","anatara",
    "katara","corniche","museum of islamic art","national museum",
]

RECOMMENDATION_WORDS=[
    "cafe","coffee","qahwa","karak","dates","restaurant","spot","bar","pub",
    "club","nightclub","nightlife","lounge","drink","party","event","events",
    "photo","photos","photography","scenic","landmark","landmarks","resort",
]


def _is_local_query(query):
    q=query.lower()
    return any(word in q for word in LOCAL_SCOPE_WORDS)


def _is_local_recommendation_query(query):
    q=query.lower()
    return _is_local_query(q) and any(word in q for word in RECOMMENDATION_WORDS)


def _has_local_signal(text):
    joined=text.lower()
    if any(word in joined for word in LOCAL_SCOPE_WORDS):
        return True
    return any(domain in joined for domain in OFFICIAL_OR_USEFUL_DOMAINS)


def web_search(query,num_results=5):
    results=[]
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query,max_results=num_results+12):
                title=item.get("title","")
                link=item.get("href","")
                snippet=item.get("body","")
                joined=f"{title} {link} {snippet}".lower()

                # Qatar-local queries must stay Qatar-local. If a result has no local signal,
                # do not hand it to Fanar.
                if _is_local_query(query) and not _has_local_signal(joined):
                    continue

                if _is_local_query(query):
                    if any(hint in joined for hint in BAD_SNIPPET_HINTS) and not _has_local_signal(joined):
                        continue

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
    for test in ["licensed hotel bars nightlife lounges near Msheireb Downtown Doha Qatar", "qahwa dates cafe near Msheireb Doha"]:
        print("QUERY:",test)
        for result in web_search(test):
            print(result)
