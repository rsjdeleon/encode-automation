mov_url = "1FAIpQLScpCB5bEiW4pUqS03aZS3SLsNyFnFS7eCxHkAP8YVMN78x0lA"
offline_url = "1FAIpQLSecVcQFhHGN5cc7XBO8kgJRbc14Q5gM4A88GJz3GxSuk61HJQ"
website_url = "https://crims.dswd.gov.ph/"

gender_list = ["Male", "Female"]

civil_status_list = [
    ("Single", "Single"),
    ("Married", "Married"),
    ("Widow/Widower", "Widow/Widower"),
    ("Separated", "Seperated"),
    ("Common-Law", "Common-Law"),
]

fund_source_list = [
    ("AKAP", "AKAP Fund 2025"),
    ("PSIF 2025", "PSIF 2025"),
]

target_sector_list = [
    "Family Heads and Other Needy Adult",
    "Women in Especially Difficult Circumstances",
    "Persons with Disabilities",
    "Senior Citizens",
    "Children in Need of Special Protection",
    "Youth in Need of Special Protection",
    "Person with Special Needs",
    "Persons Living with HIV"
]

mode_of_release = [
    "CASH",
    "GUARANTEE LETTER",
    "TICKET"
]

financial_assistance_list = [
    "Medical",
    "Burial",
    "Transportation",
    "Cash Support",
    "Food Subsidy"
]

relationship_list = [
    ("Self", "Not Specified"),
    ("Spouse", "Spouse"),
    ("Sibling", "Sibling"),
    ("Child", "Child"),
    ("Grandmother / Grand father", "Grand-parent"),
    ("In law", "In-laws"),
    ("Common Law Partner", "Common-law Spouse"),
    ("Aunty/Uncle", "Uncle/Aunty"),
    ("Parent", "Parents"),
    ("Cousin", "Cousin")
]

list_of_city = [
    "CITY OF MALABON",
    "CITY OF NAVOTAS",
    "CITY OF VALENZUELA",  
    "CITY OF CALOOCAN",  # "KALOOKAN CITY"

    "QUIAPO" ,
    "TONDO" ,
    "BINONDO" ,
    "SAN NICOLAS" ,
    "SANTA CRUZ" ,
    "SAMPALOC" ,
    "SAN MIGUEL" ,
    "ERMITA" ,
    "INTRAMUROS" ,
    "MALATE" ,
    "PACO" ,
    "PANDACAN" ,
    "PORT AREA" ,
    "SANTA ANA" ,

    "CITY OF MANDALUYONG",
    "CITY OF MARIKINA" ,
    "CITY OF PASIG" ,
    "CITY OF SAN JUAN" ,
    "QUEZON CITY" ,

    "CITY OF LAS PIÑAS" ,
    "CITY OF MAKATI" ,
    "CITY OF MUNTINLUPA" ,
    "CITY OF PARAÑAQUE" ,
    "PASAY CITY" ,
    "TAGUIG CITY" ,
    "PATEROS" ,

    "NONE OF THE ABOVE"
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

approved_by_list = {
    "Anthony Lisondra Alcantara": "ANTHONY LISONDRA ALCANTARA",
    "Maricel M. Barnedo": "MARICEL M BARNEDO",
    "Miriam C. Navarro": "MIRIAM C. NAVARRO",
    "Michael J. Lorico": "MICHAEL JOSEPH J LORICO",
    "Roy V. Barber": "ROY V BARBER"
}

approver_list = {
    "JEREMIAH JOE   FAROL",                                
    "EDWIN SUS MORATA",                                 
    "EDNA J. SACEDOR ",                                  
    "MANUELA M. LOZA",                                   
    "Maria Rosario C. Cuaresma",                                   
    "Rowela F. Hizon",                                   
    "JOHNSON B BALBERO",                                   
    "KRISHNA MEI A. SALAZAR",                                   
    "GLENDA M. DERLA",                                   
    "FERDINAND LAZARO D. BUDENG",                                   
    "LEA MAE BALORO SWINDLER",                                          
    "ABEGAIL LAGAYAN DAGA"                                   
}          

client_sub_category = {
    "Physical Disability": "Physical Disability",
    "Street Dwellers":"Street Dwellers",
    "Solo Parents":"Solo Parents",
    "Indigineous People":"Indigineous People",
    "4P'S Beneficiary":"4P'S Beneficiary",
    "Hearing/Speech Impaired":"Hearing/Speech Impaired",
    "Visually impaired":"Visually impaired",
    "Mental Disability":"Mental Disability",
    "Victims of Illegal Recruitment":"Victims of Illegal Recruitment",
    "Surrendered drug users":"Surrendered drug users",
    "Repatriated OFW":"Repatriated OFW",
    "Killed in Action (KIA)":"Killed in Action (KIA)",
    "Wounded in Action (WIA)":"Wounded in Action (WIA)",
    "Mental Disabilities":"Mental Disabilities",
    "Indigenous People":"Indigenous People",
    "Individuals with Cancer":"Individuals with Cancer",
    "Persons of Concerns - Ayslum Seeker":"Persons of Concerns - Ayslum Seeker",
    "Former Rebels":"Former Rebels",
    "Dialysis Patient":"Dialysis Patient",
    "Tuberculosis Patient":"Tuberculosis Patient",
    "Person of Concerns - Refugees":"Person of Concerns - Refugees",
    "Person of Concerns - Stateless Persons":"Person of Concerns - Stateless Persons",
    "Psychosocial Disability":"Psychosocial Disability",
    "Non-apparent cancer":"Non-apparent cancer",
    "Non-apparent rare disease":"Non-apparent rare disease",
    "Multiple disabilities":"Multiple disabilities"
}              
