mov_url = "1FAIpQLScpCB5bEiW4pUqS03aZS3SLsNyFnFS7eCxHkAP8YVMN78x0lA"
offline_url = "1FAIpQLSecVcQFhHGN5cc7XBO8kgJRbc14Q5gM4A88GJz3GxSuk61HJQ"
website_url = "https://crims.dswd.gov.ph/"

gender_list = [
    ("Male", "Male", "Male"),
    ("Female", "Female", "Female"),
]

mode_of_admission_list = [
    ("On-site", "On-site"),
    ("Walk-in", "Walk-in"),
    ("Referral", "Referral"),
]

civil_status_list = [
    ("Single", "Single", "Single"),
    ("Married", "Married", "Married"),
    ("Widow/Widower", "Widow/Widower", "Widow/Widower"),
    ("Separated", "Seperated", "Seperated"),
    ("Common-Law", "Common-Law", "Common-Law"),
]

fund_source_list = [
    ("AKAP", "AKAP Fund 2025", "AKAP Fund 2025"),
    ("PSIF 2025", "PSIF 2025", "PSIF 2025"),
]

target_sector_list = [
    ("Family Heads and Other Needy Adult", "Family Heads and Other Needy Adult", "Family Heads and Other Needy Adult"),
    ("Women in Especially Difficult Circumstances", "Women in Especially Difficult Circumstances", "Women in Especially Difficult Circumstances"),
    ("Persons with Disabilities", "Persons with Disabilities", "Persons with Disabilities"),
    ("Senior Citizens", "Senior Citizens", "Senior Citizens"),
    ("Children in Need of Special Protection", "Children in Need of Special Protection", "Children in Need of Special Protection"),
    ("Youth in Need of Special Protection", "Youth in Need of Special Protection", "Youth in Need of Special Protection"),
    ("Person with Special Needs", "Person with Special Needs", "Person with Special Needs"),
    ("Persons Living with HIV", "Persons Living with HIV", "Persons Living with HIV"),
]

mode_of_release = [
    ("CASH", "CASH", "CASH"),
    ("GUARANTEE LETTER", "GUARANTEE LETTER", "GUARANTEE LETTER"),
    ("TICKET", "TICKET", "TICKET"),
]

financial_assistance_list = [
    ("Medical", "Medical", "Medical"),
    ("Burial", "Burial", "Burial"),
    ("Transportation", "Transportation", "Transportation"),
    ("Cash Support", "Cash Support", "Cash Support"),
    ("Food Subsidy", "Food Subsidy", "Food Subsidy"),
]

relationship_list = [
    ("Self", "Not Specified", "Not Specified"),
    ("Spouse", "Spouse", "Spouse"),
    ("Sibling", "Sibling", "Sibling"),
    ("Child", "Child", "Child"),
    ("Grandmother / Grand father", "Grand-parent", "Grand-parent"),
    ("In law", "In-laws", "In-laws"),
    ("Common Law Partner", "Common-law Spouse", "Common-law Spouse"),
    ("Aunty/Uncle", "Uncle/Aunty", "Uncle/Aunty"),
    ("Parent", "Parents", "Parents"),
    ("Cousin", "Cousin", "Cousin"),
]

list_of_city = [
    ("CITY OF MALABON", "CITY OF MALABON", "CITY OF MALABON"),
    ("CITY OF NAVOTAS", "CITY OF NAVOTAS", "CITY OF NAVOTAS"),
    ("CITY OF VALENZUELA", "CITY OF VALENZUELA", "CITY OF VALENZUELA"),
    ("CITY OF CALOOCAN", "CITY OF CALOOCAN", "KALOOKAN CITY"),

    ("QUIAPO", "QUIAPO", "QUIAPO"),
    ("TONDO", "TONDO", "TONDO"),
    ("BINONDO", "BINONDO", "BINONDO"),
    ("SAN NICOLAS", "SAN NICOLAS", "SAN NICOLAS"),
    ("SANTA CRUZ", "SANTA CRUZ", "SANTA CRUZ"),
    ("SAMPALOC", "SAMPALOC", "SAMPALOC"),
    ("SAN MIGUEL", "SAN MIGUEL", "SAN MIGUEL"),
    ("ERMITA", "ERMITA", "ERMITA"),
    ("INTRAMUROS", "INTRAMUROS", "INTRAMUROS"),
    ("MALATE", "MALATE", "MALATE"),
    ("PACO", "PACO", "PACO"),
    ("PANDACAN", "PANDACAN", "PANDACAN"),
    ("PORT AREA", "PORT AREA", "PORT AREA"),
    ("SANTA ANA", "SANTA ANA", "SANTA ANA"),

    ("CITY OF MANDALUYONG", "CITY OF MANDALUYONG", "CITY OF MANDALUYONG"),
    ("CITY OF MARIKINA", "CITY OF MARIKINA", "CITY OF MARIKINA"),
    ("CITY OF PASIG", "CITY OF PASIG", "CITY OF PASIG"),
    ("CITY OF SAN JUAN", "CITY OF SAN JUAN", "CITY OF SAN JUAN"),
    ("QUEZON CITY", "QUEZON CITY", "QUEZON CITY"),

    ("CITY OF LAS PIÑAS", "CITY OF LAS PIÑAS", "CITY OF LAS PIÑAS"),
    ("CITY OF MAKATI", "CITY OF MAKATI", "CITY OF MAKATI"),
    ("CITY OF MUNTINLUPA", "CITY OF MUNTINLUPA", "CITY OF MUNTINLUPA"),
    ("CITY OF PARAÑAQUE", "CITY OF PARAÑAQUE", "CITY OF PARAÑAQUE"),
    ("PASAY CITY", "PASAY CITY", "PASAY CITY"),
    ("TAGUIG CITY", "TAGUIG CITY", "TAGUIG CITY"),
    ("PATEROS", "PATEROS", "PATEROS"),

    ("NONE OF THE ABOVE", "NONE OF THE ABOVE", "NONE OF THE ABOVE"),
]

district_city = {
    "CITY OF MALABON": "NCR THIRD DISTRICT",
    "CITY OF NAVOTAS": "NCR THIRD DISTRICT",
    "CITY OF VALENZUELA": "NCR THIRD DISTRICT",  
    "CITY OF CALOOCAN": "NCR THIRD DISTRICT",  # "KALOOKAN CITY"

    "QUIAPO":"NCR FIRST DISTRICT",
    "TONDO":"NCR FIRST DISTRICT",
    "BINONDO":"NCR FIRST DISTRICT",
    "SAN NICOLAS":"NCR FIRST DISTRICT",
    "SANTA CRUZ":"NCR FIRST DISTRICT",
    "SAMPALOC":"NCR FIRST DISTRICT",
    "SAN MIGUEL":"NCR FIRST DISTRICT",
    "ERMITA":"NCR FIRST DISTRICT",
    "INTRAMUROS":"NCR FIRST DISTRICT",
    "MALATE":"NCR FIRST DISTRICT",
    "PACO":"NCR FIRST DISTRICT",
    "PANDACAN":"NCR FIRST DISTRICT",
    "PORT AREA":"NCR FIRST DISTRICT",
    "SANTA ANA":"NCR FIRST DISTRICT",

    "CITY OF MANDALUYONG": "NCR SECOND DISTRICT",
    "CITY OF MARIKINA": "NCR SECOND DISTRICT",
    "CITY OF PASIG": "NCR SECOND DISTRICT",
    "CITY OF SAN JUAN": "NCR SECOND DISTRICT",
    "QUEZON CITY": "NCR SECOND DISTRICT",

    "CITY OF LAS PIÑAS": "NCR FOURTH DISTRICT",
    "CITY OF MAKATI": "NCR FOURTH DISTRICT",
    "CITY OF MUNTINLUPA": "NCR FOURTH DISTRICT",
    "CITY OF PARAÑAQUE": "NCR FOURTH DISTRICT",
    "PASAY CITY": "NCR FOURTH DISTRICT",
    "TAGUIG CITY": "NCR FOURTH DISTRICT",
    "PATEROS": "NCR FOURTH DISTRICT",
}

region_list = [
    ("NCR (National Capital Region)", "NCR (National Capital Region)", "NCR [National Capital Region]"),
]

province_list = [
    ("NCR FIRST DISTRICT", "NCR FIRST DISTRICT", "NCR FIRST DISTRICT"),
    ("NCR SECOND DISTRICT", "NCR SECOND DISTRICT", "NCR SECOND DISTRICT"),
    ("NCR THIRD DISTRICT", "NCR THIRD DISTRICT", "NCR THIRD DISTRICT"),
    ("NCR FOURTH DISTRICT", "NCR FOURTH DISTRICT", "NCR FOURTH DISTRICT"),
]

approved_by_list = [
    ("Anthony L. Alcantara", "Anthony L. Alcantara", "ANTHONY LISONDRA ALCANTARA"),
    ("Maricel M. Barnedo", "Maricel M. Barnedo", "MARICEL M BARNEDO"),
    ("Miriam C. Navarro", "Miriam C. Navarro", "MIRIAM C. NAVARRO"),
    ("Michael J. Lorico", "Michael J. Lorico", "MICHAEL JOSEPH J LORICO"),
    ("Roy V. Barber", "Roy V. Barber", "ROY V BARBER"),
]

client_sub_category = [
    ("Physical Disability", "Physical Disability", "Physical Disability"),
    ("Street Dwellers", "Street Dwellers", "Street Dwellers"),
    ("Solo Parents", "Solo Parents", "Solo Parents"),
    ("Indigineous People", "Indigineous People", "Indigineous People"),
    ("4P'S Beneficiary", "4P'S Beneficiary", "4P'S Beneficiary"),
    ("Hearing/Speech Impaired", "Hearing/Speech Impaired", "Hearing/Speech Impaired"),
    ("Visually impaired", "Visually impaired", "Visually impaired"),
    ("Mental Disability", "Mental Disability", "Mental Disability"),
    ("Victims of Illegal Recruitment", "Victims of Illegal Recruitment", "Victims of Illegal Recruitment"),
    ("Surrendered drug users", "Surrendered drug users", "Surrendered drug users"),
    ("Repatriated OFW", "Repatriated OFW", "Repatriated OFW"),
    ("Killed in Action (KIA)", "Killed in Action (KIA)", "Killed in Action (KIA)"),
    ("Wounded in Action (WIA)", "Wounded in Action (WIA)", "Wounded in Action (WIA)"),
    ("Mental Disabilities", "Mental Disabilities", "Mental Disabilities"),
    ("Indigenous People", "Indigenous People", "Indigenous People"),
    ("Individuals with Cancer", "Individuals with Cancer", "Individuals with Cancer"),
    ("Persons of Concerns - Ayslum Seeker", "Persons of Concerns - Ayslum Seeker", "Persons of Concerns - Ayslum Seeker"),
    ("Former Rebels", "Former Rebels", "Former Rebels"),
    ("Dialysis Patient", "Dialysis Patient", "Dialysis Patient"),
    ("Tuberculosis Patient", "Tuberculosis Patient", "Tuberculosis Patient"),
    ("Person of Concerns - Refugees", "Person of Concerns - Refugees", "Person of Concerns - Refugees"),
    ("Person of Concerns - Stateless Persons", "Person of Concerns - Stateless Persons", "Person of Concerns - Stateless Persons"),
    ("Psychosocial Disability", "Psychosocial Disability", "Psychosocial Disability"),
    ("Non-apparent cancer", "Non-apparent cancer", "Non-apparent cancer"),
    ("Non-apparent rare disease", "Non-apparent rare disease", "Non-apparent rare disease"),
    ("Multiple disabilities", "Multiple disabilities", "Multiple disabilities"),
]
