
import random
import string

l1 = []
l2 = []

ISBN_13 = [9788579620560,
9780241953242,
9780771008795,
9780753553343,
9788575593219,
9781408808207,
9789198577815,
9780451524935,
9788129116123,
9780099572862,
9781938793196,
9781439149898,
9789960897288,
9788170286929,
9788170287919,
9781101137192,
9781588368980,
9780143190851,
9781101137185,
9780316769532,
9781982122355,
9780735211292,
9781684032617,
9781876963460,
9781467776219,
9780547572178,
9789354860676,
9781250256744,
9781625790705,
9781542043533,
9781542090070,
9781542027250,
9781618243423,
9781416520603,
9781477809785,
9781477817407,
9781477828311,
9781503950320,
9781503940710,
9780743499194,
9781542048460,
9780765389138,
9781606998298,
9781423174769,
9781250275042,
9780062981011,
9781087983769,
9781250214713,
9781250186928,
9781250185433,
9781250185464,
9781250229847,
9781250765383,
9781529051919,
9781250236333,
9780316705882,
9780671720377,
9785555875693,
9781922323972,
9781973292418,
9780990880028,
9780857669636,
9780575129061,
9780316462457,
9780316462488,
9780316462549]

Titles = ["https://seven-forward.com/images/Lolita.jpg",
"https://seven-forward.com/images/Lolita.jpg",
"https://seven-forward.com/images/TheHandmaidsTale0.jpg",
"https://seven-forward.com/images/TheRodchenkovAffair.jpg",
"https://seven-forward.com/images/OCapitalLivro.jpg",
"https://seven-forward.com/images/TheGraveyardBook.jpg",
"https://seven-forward.com/images/NineteenEightyFour.jpg",
"https://seven-forward.com/images/AnimalFarm.jpg",
"https://seven-forward.com/images/TheBoyintheStripedPyjamas.jpg",
"https://seven-forward.com/images/EverythingThatRemains.jpg",
"https://seven-forward.com/images/AllThatRemains.jpg",
"https://seven-forward.com/images/WhenTheMoonSplit.jpg",
"https://seven-forward.com/images/DiwaneGhalib.jpg",
"https://seven-forward.com/images/ThebestofFaizAhmedFaiz.jpg",
"https://seven-forward.com/images/AtlasShrugged.jpg",
"https://seven-forward.com/images/EngineersofVictory.jpg",
"https://seven-forward.com/images/SuperFresh.jpg",
"https://seven-forward.com/images/TheFountainhead.jpg",
"https://seven-forward.com/images/TheCatcherintheRye.jpg",
"https://seven-forward.com/images/DeceptionPoint.jpg",
"https://seven-forward.com/images/AtomicHabits.jpg",
"https://seven-forward.com/images/ARadicalGuideforWomenwithADHD.jpg",
"https://seven-forward.com/images/TheStarsMyDestination.jpg",
"https://seven-forward.com/images/TheWaroftheWorlds.jpg",
"https://seven-forward.com/images/AScannerDarkly.jpg",
"https://seven-forward.com/images/AroundtheWorldin80Days.jpg",
"https://seven-forward.com/images/AxiomsEnd.jpg",
"https://seven-forward.com/images/AtlasShrugged.jpg",
"https://seven-forward.com/images/Aftershocks.jpg",
"https://seven-forward.com/images/Ballistic.jpg",
"https://seven-forward.com/images/Citadel.jpg"]

def result():
    ind = 0
    for i in range (66):
        dic = {}
        dic["user_id"] = str(i)
        dic["access_token"] = str(i)*2
        dic["database_id"] = str(i)*3
        dic["is_Revoked"] = False
        dic["new_book_identifiers"] = []
        randnum = random.randint(0,5)
        for num in range(randnum):
            isbn_13 = str(ISBN_13[ind])
            dic["new_book_identifiers"].append({"Type": "ISBN_13", "Value": isbn_13})
        ind = ind + 1
        l1.append(dic)

    ind = 0
    for i in range (66, 97):
        dic = {}
        dic["user_id"] = str(i)
        dic["access_token"] = str(i)*2
        dic["database_id"] = str(i)*3
        dic["is_Revoked"] = False
        dic["new_book_identifiers"] = []
        randnum = random.randint(0, 5)
        for num in range(randnum):
            title = Titles[ind].replace("https://seven-forward.com/images/", "").replace(".jpg", "")
            dic["new_book_identifiers"].append({"Type": "Title", "Value": title})
        ind = ind + 1
        l2.append(dic)

    return (l1 + l2)

