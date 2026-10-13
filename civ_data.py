# civ_data.py

civs = {
    "armenians": {
        "summary": "Armenians are versatile with strong gunpowder units, cavalry, and economic bonuses.",
        "units": {
            "Cavalry": ["Cavalry Archer", "Elite Camel"],
            "Ranged": ["Hand Cannoneer", "Bombard Cannon"],
            "Infantry": ["Halberdier"]
        },
        "counters": {
            "Cavalry Archer": ["Skirmisher", "Spearmen"],
            "Elite Camel": ["Pikemen", "Scorpions"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Bombard Cannon": ["Cavalry", "Infantry"],
            "Halberdier": ["Archers", "Cavalry"]
        }
    },
    "aztecs": {
        "summary": "Aztecs excel in infantry and monks with strong economy and military presence.",
        "units": {
            "Infantry": ["Jaguar Warrior", "Eagle Warrior"],
            "Ranged": ["Arbalest", "Plumed Archer"],
            "Siege": ["Onager"]
        },
        "counters": {
            "Jaguar Warrior": ["Cavalry", "Archers"],
            "Eagle Warrior": ["Spearmen", "Pikemen"],
            "Arbalest": ["Cavalry", "Skirmisher"],
            "Plumed Archer": ["Hand Cannoneer", "Cavalry Archers"],
            "Onager": ["Cavalry", "Skirmishers"]
        }
    },
    "bengalis": {
        "summary": "Bengalis have a strong navy and elephant units, excelling in economy and heavy cavalry.",
        "units": {
            "Cavalry": ["Elite Battle Elephant", "Cavalry Archer"],
            "Ranged": ["Hand Cannoneer"],
            "Infantry": ["Elite Musketman"]
        },
        "counters": {
            "Elite Battle Elephant": ["Pikemen", "Halberdiers"],
            "Cavalry Archer": ["Skirmisher", "Spearmen"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Elite Musketman": ["Cavalry", "Skirmisher"]
        }
    },
    "berbers": {
        "summary": "Berbers are swift cavalry experts with strong camels and unique economy bonuses.",
        "units": {
            "Cavalry": ["Camel Archer", "Genitour", "Camel Rider"],
            "Ranged": ["Arbalest"],
            "Infantry": ["Champion"]
        },
        "counters": {
            "Camel Archer": ["Skirmisher", "Spearmen"],
            "Genitour": ["Cavalry", "Skirmisher"],
            "Camel Rider": ["Pikemen", "Halberdier"],
            "Arbalest": ["Cavalry", "Skirmisher"],
            "Champion": ["Archers", "Cavalry"]
        }
    },
    "bohemians": {
        "summary": "Bohemians are a versatile civilization with strong gunpowder units and robust economy.",
        "units": {
            "Cavalry": ["Hussite Wagon", "Hussar"],
            "Ranged": ["Hand Cannoneer", "Crossbowman"],
            "Siege": ["Cannon Galleon"]
        },
        "counters": {
            "Hussite Wagon": ["Cavalry", "Infantry"],
            "Hussar": ["Pikemen", "Halberdier"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Crossbowman": ["Cavalry", "Skirmisher"],
            "Cannon Galleon": ["Fast Fire Ship", "Cannon Galleon"]
        }
    },
    "britons": {
        "summary": "Britons specialize in archery with cheaper town centers and excellent foot archers.",
        "units": {
            "Ranged": ["Longbowman", "Arbalest"],
            "Infantry": ["Champion"],
            "Cavalry": ["Paladin"]
        },
        "counters": {
            "Longbowman": ["Cavalry", "Skirmisher"],
            "Arbalest": ["Cavalry", "Skirmisher"],
            "Champion": ["Archers", "Cavalry"],
            "Paladin": ["Pikemen", "Halberdier"]
        }
    },
    "bulgarians": {
        "summary": "Bulgarians excel with strong infantry and versatile cavalry, supported by cheap blacksmith upgrades.",
        "units": {
            "Infantry": ["Halberdier", "Champion", "Two-Handed Swordsman"],
            "Cavalry": ["Hussar", "Paladin"],
            "Ranged": ["Crossbowman"]
        },
        "counters": {
            "Halberdier": ["Skirmisher", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Two-Handed Swordsman": ["Archers", "Cavalry"],
            "Hussar": ["Pikemen", "Halberdier"],
            "Paladin": ["Pikemen", "Halberdier"],
            "Crossbowman": ["Cavalry", "Skirmisher"]
        }
    },
    "burgundians": {
        "summary": "Burgundians are cavalry-focused with powerful knights and unique economic bonuses through their stables.",
        "units": {
            "Cavalry": ["Knight", "Paladin", "Throwing Axeman"],
            "Ranged": ["Crossbowman"],
            "Siege": ["Cannon Galleon"]
        },
        "counters": {
            "Knight": ["Pikemen", "Spearmen"],
            "Paladin": ["Pikemen", "Camels"],
            "Throwing Axeman": ["Cavalry", "Skirmisher"],
            "Crossbowman": ["Cavalry", "Skirmisher"],
            "Cannon Galleon": ["Fast Fire Ship", "Cannon Galleon"]
        }
    },
    "burmese": {
        "summary": "Burmese have strong infantry and archers, supported by cheaper monks and faster working lumberjacks.",
        "units": {
            "Infantry": ["Arambai", "Champion"],
            "Ranged": ["Archer", "Crossbowman"],
            "Cavalry": ["Light Cavalry", "Hussar"]
        },
        "counters": {
            "Arambai": ["Spearmen", "Skirmisher"],
            "Champion": ["Archers", "Cavalry"],
            "Archer": ["Cavalry", "Skirmisher"],
            "Crossbowman": ["Cavalry", "Skirmisher"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Hussar": ["Spearmen", "Pikemen"]
        }
    },
    "byzantines": {
        "summary": "Byzantines have a versatile, defensive playstyle with strong buildings and cheap counter units.",
        "units": {
            "Infantry": ["Spearman", "Halberdier", "Champion"],
            "Cavalry": ["Camel", "Cataphract"],
            "Ranged": ["Skirmisher", "Arbalest"]
        },
        "counters": {
            "Spearman": ["Archers", "Skirmisher"],
            "Halberdier": ["Archers", "Skirmisher"],
            "Champion": ["Archers", "Cavalry"],
            "Camel": ["Pikemen", "Spearmen"],
            "Cataphract": ["Pikemen", "Camels"],
            "Skirmisher": ["Cavalry", "Man-at-Arms"],
            "Arbalest": ["Cavalry", "Skirmisher"]
        }
    },
    "celts": {
        "summary": "Celts are known for their fast infantry, powerful siege, and strong economy from faster lumberjacks.",
        "units": {
            "Infantry": ["Woad Raider", "Champion", "Two-Handed Swordsman"],
            "Siege": ["Woad Raider", "Siege Onager"],
            "Ranged": ["Skirmisher"]
        },
        "counters": {
            "Woad Raider": ["Spearmen", "Archers"],
            "Champion": ["Archers", "Cavalry"],
            "Two-Handed Swordsman": ["Archers", "Cavalry"],
            "Siege Onager": ["Cavalry", "Infantry"],
            "Skirmisher": ["Cavalry", "Man-at-Arms"]
        }
    },
    "chinese": {
        "summary": "Chinese have a flexible economy with cheaper technologies, strong archers, and a variety of units.",
        "units": {
            "Infantry": ["Chu Ko Nu", "Champion"],
            "Ranged": ["Chu Ko Nu", "Crossbowman"],
            "Cavalry": ["Cavalry Archer", "Knight"]
        },
        "counters": {
            "Chu Ko Nu": ["Skirmisher", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Crossbowman": ["Cavalry", "Skirmisher"],
            "Cavalry Archer": ["Spearmen", "Skirmisher"],
            "Knight": ["Pikemen", "Spearmen"]
        }
    },
    "cumans": {
        "summary": "Cumans excel at fast-paced cavalry and have the unique ability to build two Town Centers in the Feudal Age.",
        "units": {
            "Cavalry": ["Light Cavalry", "Knight", "Camel"],
            "Infantry": ["Militia", "Man-at-Arms", "Champion"],
            "Ranged": ["Skirmisher", "Archer"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Camel": ["Pikemen", "Spearmen"],
            "Militia": ["Archers", "Spearmen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Skirmisher": ["Cavalry", "Man-at-Arms"],
            "Archer": ["Skirmisher", "Cavalry"]
        }
    },
    "dravidians": {
        "summary": "Dravidians focus on a strong infantry and elephant-based army with powerful siege capabilities.",
        "units": {
            "Infantry": ["Swordsman", "Champion"],
            "Elephants": ["War Elephant", "Elite War Elephant"],
            "Ranged": ["Hand Cannoneer", "Archer"]
        },
        "counters": {
            "Swordsman": ["Archers", "Pikemen"],
            "Champion": ["Archers", "Cavalry"],
            "War Elephant": ["Pikemen", "Camels", "Scorpions"],
            "Elite War Elephant": ["Pikemen", "Camels", "Scorpions"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"]
        }
    },
    "ethiopians": {
        "summary": "Ethiopians focus on archery and fast infantry with a strong economy and faster firing archers.",
        "units": {
            "Cavalry": ["Hussar", "Light Cavalry"],
            "Ranged": ["Arbalest", "Shotel Warrior"],
            "Siege": ["Mangonel"]
        },
        "counters": {
            "Hussar": ["Spearmen", "Pikemen"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Arbalest": ["Skirmisher", "Cavalry"],
            "Shotel Warrior": ["Spearmen", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"]
        }
    },
    "franks": {
        "summary": "Franks specialize in strong cavalry charges with powerful Knights and Paladins and a boosted economy.",
        "units": {
            "Cavalry": ["Knight", "Paladin", "Throwing Axeman"],
            "Infantry": ["Throwing Axeman", "Man-at-Arms"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Knight": ["Pikemen", "Camels"],
            "Paladin": ["Pikemen", "Camels"],
            "Throwing Axeman": ["Cavalry", "Skirmisher"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "georgians": {
        "summary": "Georgians boast strong infantry and defensive structures with an emphasis on monks and siege weapons.",
        "units": {
            "Infantry": ["Spearman", "Champion"],
            "Monks": ["Monk"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Spearman": ["Archers", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Monk": ["Cavalry", "Infantry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "goths": {
        "summary": "Goths excel at mass infantry production with cheap units and strong late-game spam tactics.",
        "units": {
            "Infantry": ["Militia", "Man-at-Arms", "Champion", "Huskarl"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Militia": ["Archers", "Spearmen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Huskarl": ["Skirmisher", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "gurjaras": {
        "summary": "Gurjaras focus on strong cavalry and siege units with an economic bonus from cheaper villagers.",
        "units": {
            "Cavalry": ["Camel", "Knight"],
            "Infantry": ["Spearman", "Man-at-Arms"],
            "Siege": ["Mangonel", "Scorpion"]
        },
        "counters": {
            "Camel": ["Pikemen", "Spearmen"],
            "Knight": ["Pikemen", "Camels"],
            "Spearman": ["Archers", "Cavalry"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Scorpion": ["Cavalry", "Infantry"]
        }
    },
    "hindustanis": {
        "summary": "Hindustanis have a balanced army with strong elephants and cavalry alongside powerful archers.",
        "units": {
            "Elephants": ["War Elephant", "Elite War Elephant"],
            "Cavalry": ["Knight", "Camel"],
            "Ranged": ["Archer", "Hand Cannoneer"]
        },
        "counters": {
            "War Elephant": ["Pikemen", "Camels"],
            "Elite War Elephant": ["Pikemen", "Camels"],
            "Knight": ["Pikemen", "Camels"],
            "Camel": ["Pikemen", "Spearmen"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"]
        }
    },
    "huns": {
        "summary": "Huns are aggressive cavalry with strong early pressure, lacking need for houses due to population bonus.",
        "units": {
            "Cavalry": ["Light Cavalry", "Knight", "Cavalry Archer"],
            "Infantry": ["Man-at-Arms"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Cavalry Archer": ["Skirmisher", "Cavalry"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "incas": {
        "summary": "Incas have versatile infantry and strong economy with unique units like Kamayuk and Slingers.",
        "units": {
            "Infantry": ["Slinger", "Kamayuk", "Champion"],
            "Cavalry": ["Light Cavalry", "Jaguar Warrior"],
            "Ranged": ["Archer"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Slinger": ["Skirmisher", "Cavalry"],
            "Kamayuk": ["Cavalry", "Skirmisher"],
            "Champion": ["Archers", "Cavalry"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Jaguar Warrior": ["Skirmisher", "Eagle Warrior"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "indians": {
        "summary": "Indians excel with strong elephants and economic bonuses, supported by versatile infantry and archers.",
        "units": {
            "Elephants": ["War Elephant", "Elite War Elephant"],
            "Infantry": ["Spearman", "Champion"],
            "Ranged": ["Archer", "Hand Cannoneer"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "War Elephant": ["Pikemen", "Camels"],
            "Elite War Elephant": ["Pikemen", "Camels"],
            "Spearman": ["Archers", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "italians": {
        "summary": "Italians have cheaper naval units and a flexible army with strong infantry and archers.",
        "units": {
            "Infantry": ["Militia", "Man-at-Arms", "Champion"],
            "Ranged": ["Crossbowman", "Arbalest"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Militia": ["Archers", "Spearmen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Arbalest": ["Skirmisher", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "japanese": {
        "summary": "Japanese have strong infantry with fast attack speeds and excellent fishing economy.",
        "units": {
            "Infantry": ["Samurai", "Champion", "Halberdier"],
            "Ranged": ["Archer", "Crossbowman"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Samurai": ["Eagle Warrior", "Skirmisher"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "jurchens": {
        "summary": "Jurchens have powerful infantry and strong siege units, focusing on early aggression.",
        "units": {
            "Infantry": ["Man-at-Arms", "Champion", "Halberdier"],
            "Ranged": ["Archer", "Crossbowman"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Siege": ["Siege Onager", "Trebuchet"]
        },
        "counters": {
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Siege Onager": ["Cavalry", "Infantry"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "khitans": {
        "summary": "Khitans combine strong cavalry with unique units and powerful siege weaponry.",
        "units": {
            "Cavalry": ["Light Cavalry", "Knight", "Camel Rider"],
            "Ranged": ["Archer", "Mangudai"],
            "Infantry": ["Spearman", "Halberdier"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Camel Rider": ["Pikemen", "Camels"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Mangudai": ["Spearmen", "Skirmisher"],
            "Spearman": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "khmer": {
        "summary": "Khmer have powerful siege and elephants with a strong economy and versatile army.",
        "units": {
            "Elephants": ["Battle Elephant", "Elite Battle Elephant"],
            "Infantry": ["Champion", "Halberdier"],
            "Ranged": ["Archer", "Cavalry Archer"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Battle Elephant": ["Pikemen", "Camels"],
            "Elite Battle Elephant": ["Pikemen", "Camels"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Cavalry Archer": ["Spearmen", "Skirmisher"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "koreans": {
        "summary": "Koreans excel with strong towers, powerful siege units, and versatile infantry and archers.",
        "units": {
            "Infantry": ["Spearman", "Champion", "Halberdier"],
            "Ranged": ["Archer", "Cavalry Archer"],
            "Siege": ["Siege Onager", "Bombard Cannon"],
            "Cavalry": ["Knight", "Light Cavalry"]
        },
        "counters": {
            "Spearman": ["Archers", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Cavalry Archer": ["Spearmen", "Skirmisher"],
            "Siege Onager": ["Cavalry", "Infantry"],
            "Bombard Cannon": ["Cavalry", "Infantry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"]
        }
    },
    "lithuanians": {
        "summary": "Lithuanians gain strong cavalry and monks with relic bonuses, good for aggressive play.",
        "units": {
            "Cavalry": ["Paladin", "Knight", "Scout Cavalry"],
            "Infantry": ["Man-at-Arms", "Champion"],
            "Monks": ["Monk"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Paladin": ["Pikemen", "Camels"],
            "Knight": ["Pikemen", "Camels"],
            "Scout Cavalry": ["Spearmen", "Skirmisher"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Monk": ["Cavalry", "Monk"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "magyars": {
        "summary": "Magyars specialize in fast cavalry raids with unique ranged cavalry and strong economy.",
        "units": {
            "Cavalry": ["Light Cavalry", "Knight", "Hussar"],
            "Ranged": ["Cavalry Archer", "Archer"],
            "Infantry": ["Man-at-Arms", "Champion"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Hussar": ["Spearmen", "Pikemen"],
            "Cavalry Archer": ["Spearmen", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "malay": {
        "summary": "Malay benefit from faster resource gathering and powerful naval units, with versatile infantry.",
        "units": {
            "Infantry": ["Man-at-Arms", "Champion", "Halberdier"],
            "Ranged": ["Archer", "Crossbowman"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Naval": ["War Galley", "Cannon Galleon"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "War Galley": ["Fire Ship", "Galleon"],
            "Cannon Galleon": ["Fire Ship", "Galleon"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "malians": {
        "summary": "Malians focus on strong infantry and buildings with better durability and cost efficiency.",
        "units": {
            "Infantry": ["Champion", "Halberdier", "Elite Eagle Warrior"],
            "Ranged": ["Archer", "Crossbowman"],
            "Cavalry": ["Light Cavalry", "Knight"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Elite Eagle Warrior": ["Spearmen", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "maya": {
        "summary": "Mayans have cheap archers and strong infantry with resource efficiency, excellent for ranged attacks.",
        "units": {
            "Ranged": ["Archer", "Plumed Archer"],
            "Infantry": ["Eagle Warrior", "Champion"],
            "Cavalry": ["Light Cavalry"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Archer": ["Skirmisher", "Cavalry"],
            "Plumed Archer": ["Skirmisher", "Cavalry"],
            "Eagle Warrior": ["Camels", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "mongols": {
        "summary": "Mongols have fast cavalry and powerful siege with strong hunting economy.",
        "units": {
            "Cavalry": ["Light Cavalry", "Mangudai", "Knight"],
            "Ranged": ["Archer", "Cavalry Archer"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Mangudai": ["Spearmen", "Skirmisher"],
            "Knight": ["Pikemen", "Camels"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Cavalry Archer": ["Spearmen", "Skirmisher"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "persians": {
        "summary": "Persians have strong economy with faster working villagers and powerful cavalry and elephants.",
        "units": {
            "Cavalry": ["Knight", "War Elephant", "Camel"],
            "Infantry": ["Man-at-Arms", "Champion"],
            "Ranged": ["Crossbowman", "Skirmisher"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Knight": ["Pikemen", "Camels"],
            "War Elephant": ["Pikemen", "Hand Cannoneers"],
            "Camel": ["Spearmen", "Pikemen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Skirmisher": ["Cavalry", "Man-at-Arms"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "poles": {
        "summary": "Poles are versatile with strong knights, infantry, and powerful siege, excellent for aggressive play.",
        "units": {
            "Cavalry": ["Knight", "Hussar"],
            "Infantry": ["Man-at-Arms", "Champion", "Halberdier"],
            "Ranged": ["Crossbowman", "Skirmisher"],
            "Siege": ["Onager", "Trebuchet"]
        },
        "counters": {
            "Knight": ["Pikemen", "Camels"],
            "Hussar": ["Spearmen", "Pikemen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Cavalry", "Skirmisher"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Skirmisher": ["Cavalry", "Man-at-Arms"],
            "Onager": ["Cavalry", "Infantry"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "portuguese": {
        "summary": "Portuguese excel in gunpowder and naval units, with strong economy and versatile army.",
        "units": {
            "Infantry": ["Man-at-Arms", "Champion", "Hand Cannoneer"],
            "Cavalry": ["Knight", "Hussar"],
            "Ranged": ["Crossbowman", "Skirmisher"],
            "Naval": ["Caravel", "War Galley"],
            "Siege": ["Cannon Galleon", "Trebuchet"]
        },
        "counters": {
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Knight": ["Pikemen", "Camels"],
            "Hussar": ["Spearmen", "Pikemen"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Skirmisher": ["Cavalry", "Man-at-Arms"],
            "Caravel": ["Fire Ship", "Galleon"],
            "War Galley": ["Fire Ship", "Galleon"],
            "Cannon Galleon": ["Fire Ship", "Galleon"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "romans": {
        "summary": "Romans focus on powerful infantry and siege with economic bonuses. ",
        "units": {
            "Infantry": ["Legionary", "Centurion", "Champion"],
            "Cavalry": ["Centurion"],  # Centurions are heavy cavalry unique to Romans
            "Siege": ["Scorpion", "Trebuchet"]
        },
        "counters": {
            "Legionary": ["Spearmen", "Halberdier"],
            "Centurion": ["Pikeman", "Camels"],
            "Champion": ["Pikeman", "Halberdier"],
            "Scorpion": ["Cavalry", "Infantry"],
            "Trebuchet": ["Cavalry", "Skirmisher"]
        }
    },
    "saracens": {
        "summary": "Saracens excel at versatile cavalry and strong naval power, with trade advantages.",
        "units": {
            "Cavalry": ["Camel", "Mameluke", "Knight"],
            "Ranged": ["Archer", "Hand Cannoneer"],
            "Naval": ["War Galley", "Fire Ship"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Camel": ["Pikemen", "Spearmen"],
            "Mameluke": ["Spearmen", "Halberdier"],
            "Knight": ["Pikemen", "Camels"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "War Galley": ["Fire Ship", "Cannon Galleon"],
            "Fire Ship": ["Demolition Ship", "Cannon Galleon"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "shu": {
        "summary": "Shu focus on strong infantry and unique units, supported by fast working economy.",
        "units": {
            "Infantry": ["Elite Chu Ko Nu", "Swordsman", "Champion"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Ranged": ["Chu Ko Nu"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Elite Chu Ko Nu": ["Skirmisher", "Cavalry"],
            "Swordsman": ["Archers", "Pikemen"],
            "Champion": ["Archers", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Chu Ko Nu": ["Skirmisher", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "sicilians": {
        "summary": "Sicilians have strong infantry and navy with unique knights and fast working economy.",
        "units": {
            "Infantry": ["Serjeant", "Champion", "Man-at-Arms"],
            "Cavalry": ["Knight", "Paladin"],
            "Naval": ["Galleon", "Fire Ship"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Serjeant": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Knight": ["Pikemen", "Camels"],
            "Paladin": ["Pikemen", "Camels"],
            "Galleon": ["Fire Ship", "Demolition Ship"],
            "Fire Ship": ["Demolition Ship", "Cannon Galleon"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "slavs": {
        "summary": "Slavs excel with strong infantry and farming economy, backed by powerful siege units.",
        "units": {
            "Infantry": ["Militia", "Man-at-Arms", "Champion", "Two-Handed Swordsman"],
            "Siege": ["Siege Onager", "Trebuchet"],
            "Cavalry": ["Knight", "Hussar"]
        },
        "counters": {
            "Militia": ["Archers", "Spearmen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Two-Handed Swordsman": ["Archers", "Cavalry"],
            "Siege Onager": ["Cavalry", "Infantry"],
            "Trebuchet": ["Cavalry", "Infantry"],
            "Knight": ["Pikemen", "Camels"],
            "Hussar": ["Spearmen", "Pikemen"]
        }
    },
    "spanish": {
        "summary": "Spanish have strong gunpowder units and cavalry with faster building and research times.",
        "units": {
            "Infantry": ["Conquistador", "Man-at-Arms", "Champion"],
            "Cavalry": ["Knight", "Hussar"],
            "Ranged": ["Arquebusier", "Crossbowman"],
            "Siege": ["Bombard Cannon", "Trebuchet"]
        },
        "counters": {
            "Conquistador": ["Spearmen", "Pikemen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Hussar": ["Spearmen", "Pikemen"],
            "Arquebusier": ["Cavalry", "Skirmisher"],
            "Crossbowman": ["Cavalry", "Skirmisher"],
            "Bombard Cannon": ["Cavalry", "Infantry"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "tatars": {
        "summary": "Tatars specialize in fast cavalry and versatile ranged units with strong economic bonuses.",
        "units": {
            "Cavalry": ["Light Cavalry", "Knight", "Kipchak"],
            "Ranged": ["Cavalry Archer", "Archer"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Kipchak": ["Spearmen", "Halberdier"],
            "Cavalry Archer": ["Spearmen", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "teutons": {
        "summary": "Teutons have strong infantry and siege with powerful defensive buildings and slow but heavy cavalry.",
        "units": {
            "Infantry": ["Teutonic Knight", "Champion", "Halberdier"],
            "Cavalry": ["Knight", "Paladin"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Teutonic Knight": ["Archers", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Halberdier": ["Archers", "Skirmisher"],
            "Knight": ["Pikemen", "Camels"],
            "Paladin": ["Pikemen", "Camels"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "turks": {
        "summary": "Turks focus on powerful gunpowder units and cavalry with bonuses to gold mining.",
        "units": {
            "Cavalry": ["Light Cavalry", "Knight", "Sipahi"],
            "Ranged": ["Hand Cannoneer", "Archer"],
            "Siege": ["Bombard Cannon", "Mangonel"]
        },
        "counters": {
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Knight": ["Pikemen", "Camels"],
            "Sipahi": ["Spearmen", "Halberdier"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Bombard Cannon": ["Cavalry", "Infantry"],
            "Mangonel": ["Cavalry", "Skirmisher"]
        }
    },
    "vietnamese": {
        "summary": "Vietnamese have strong archers, cheaper technologies, and versatile units with a focus on flexibility.",
        "units": {
            "Ranged": ["Rattan Archer", "Archer", "Crossbowman"],
            "Infantry": ["Militia", "Man-at-Arms"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Rattan Archer": ["Skirmisher", "Cavalry"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Militia": ["Archers", "Spearmen"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "vikings": {
        "summary": "Vikings boast strong infantry and naval units with economic bonuses from cheaper fishing ships.",
        "units": {
            "Infantry": ["Berserk", "Champion", "Swordsman"],
            "Naval": ["Longboat", "War Galley"],
            "Siege": ["Mangonel", "Onager"]
        },
        "counters": {
            "Berserk": ["Archers", "Cavalry"],
            "Champion": ["Archers", "Cavalry"],
            "Swordsman": ["Archers", "Cavalry"],
            "Longboat": ["Fire Ship", "Demolition Ship"],
            "War Galley": ["Fire Ship", "Demolition Ship"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Onager": ["Cavalry", "Infantry"]
        }
    },
    "wei": {
        "summary": "Wei excel with strong infantry and crossbowmen, focusing on siege weapons and solid economy.",
        "units": {
            "Infantry": ["Spearman", "Man-at-Arms", "Champion"],
            "Ranged": ["Crossbowman", "Hand Cannoneer"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Spearman": ["Archers", "Skirmisher"],
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Crossbowman": ["Cavalry", "Skirmisher"],
            "Hand Cannoneer": ["Cavalry", "Skirmisher"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    },
    "wu": {
        "summary": "Wu have a balanced army with strong archers, cavalry, and siege, excelling in flexible strategies.",
        "units": {
            "Infantry": ["Man-at-Arms", "Champion"],
            "Cavalry": ["Knight", "Light Cavalry"],
            "Ranged": ["Archer", "Crossbowman"],
            "Siege": ["Mangonel", "Trebuchet"]
        },
        "counters": {
            "Man-at-Arms": ["Archers", "Spearmen"],
            "Champion": ["Archers", "Cavalry"],
            "Knight": ["Pikemen", "Camels"],
            "Light Cavalry": ["Spearmen", "Pikemen"],
            "Archer": ["Skirmisher", "Cavalry"],
            "Crossbowman": ["Skirmisher", "Cavalry"],
            "Mangonel": ["Cavalry", "Skirmisher"],
            "Trebuchet": ["Cavalry", "Infantry"]
        }
    }
}
