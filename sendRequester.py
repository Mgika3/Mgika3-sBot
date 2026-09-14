import requests

def main():
    urlL2 = "https://adecampus2.univ-jfc.fr/jsp/custom/modules/plannings/anonymous_cal.jsp?data=62a62feb560cfd9d20f2729c9afa90d981a14e587ccf1e089ec047684bfb5605a56b9d48cf60d89aad5fb9b261bdf14ba18bf058bc46cf561dc64804dc61d3709f02238ffca27b04be2b92231c49ce38,1"
    reponseL2 = requests.get(urlL2)

    with open("ADECalL2.ics", "wb") as f:
        f.write(reponseL2.content)

    urlL1 = "https://adecampus2.univ-jfc.fr/jsp/custom/modules/plannings/anonymous_cal.jsp?data=89f51dd9106f8f7e0120805f4adeb0c33b7f55d33b04abb43fd5f02a41a510bda56b9d48cf60d89aad5fb9b261bdf14ba18bf058bc46cf561dc64804dc61d3709f02238ffca27b04be2b92231c49ce38,1"
    reponseL1 = requests.get(urlL1)

    with open("ADECalL1.ics", "wb") as f:
        f.write(reponseL1.content)

