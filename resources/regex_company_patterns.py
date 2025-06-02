company_regex_dict = {
    'nodes': r'\b(nodes(?:[-_ ]\w+)?)\b',  # Matches "nodes" and variations like "nodes-abc", "nodes_xyz"
    'abtion': r'(abtion(?:[-_ ]\w+)?)',  # Matches "abtion" and variations like "abtion-abc", "abtion_xyz"
    'heyday': r'(heyday(?:[-_ ]\w+)?)',  # Matches "heyday" and variations like "heyday-abc", "heyday_xyz"
    'trifork': r'(trifork(?:[-_ ]\w+)?)',  # Matches "trifork" and variations like "trifork-abc", "trifork_xyz"
    'frontit': r'(frontit(?:[-_ ]\w+)?)',  # Matches "frontit" and variations like "frontit-abc", "frontit_xyz"
    'holion': r'(holion(?:[-_ ]\w+)?)',  # Matches "holion" and variations like "holion-abc", "holion_xyz"
    'kruso': r'(kruso(?:[-_ ]\w+)?)',  # Matches "kruso" and variations like "kruso-abc", "kruso_xyz"
    'pandiweb': r'(pandi(?:[-_ ]?web))',  # Matches "pandiweb" and variations like "pandi-web", "pandi_web"
    'uptime': r'(uptime(?:[-_ ]\w+)?)',  # Matches "uptime" and variations like "uptime-abc", "uptime_xyz"
    'charlie tango': r'(charlie[-_ ]?tango)',  # Matches "charlie tango", "charlie_tango", "charlie-tango"
    'ffw': r'(ffw(?:[-_ ]\w+)?)',  # Matches "ffw" and variations like "ffw-abc", "ffw_xyz"
    'mysupport': r'(mysupport(?:[-_ ]\w+)?)',  # Matches "mysupport" and variations like "mysupport-abc", "mysupport_xyz"
    'shape': r'(shape(?:[-_ ]\w+)?)',  # Matches "shape" and variations like "shape-abc", "shape_xyz"
    'makeable': r'(makeable(?:[-_ ]\w+)?)',  # Matches "makeable" and variations like "makeable-abc", "makeable_xyz"
    'mustache': r'(mustache(?:[-_ ]\w+)?)',  # Matches "mustache" and variations like "mustache-abc", "mustache_xyz"
    'house of code': r'(house[-_ ]?of[-_ ]?code)',  # Matches "house of code", "house_of_code", "house-of-code"
    'greener pastures': r'(greener[-_ ]?pastures)',  # Matches "greener pastures", "greener_pastures", "greener-pastures"
    'axla': r'(axla)',  # Matches "axla" exactly (no variations needed)
    'snapp': r'(snapp(?:[-_ ]\w+)?)',  # Matches "snapp" and variations like "snapp-abc", "snapp_xyz"
    'appscaptain': r'(appscaptain(?:[-_ ]\w+)?)',  # Matches "appscaptain" and variations like "appscaptain-abc", "appscaptain_xyz"
    'adtomic': r'(adtomic(?:[-_ ]\w+)?)',  # Matches "adtomic" and variations like "adtomic-abc", "adtomic_xyz"
    'signifly': r'(signifly(?:[-_ ]\w+)?)',  # Matches "signifly" and variations like "signifly-abc", "signifly_xyz"
    'creuna': r'(creuna(?:[-_ ]\w+)?)',  # Matches "creuna" and variations like "creuna-abc", "creuna_xyz"
    'strømlin': r'(strømlin|stromlin)',  # Matches both "strømlin" and "stromlin" (considering possible replacement of ø with o)
    'knowit': r'(know[-_ ]?it)',  # Matches "knowit", "know_it", "know-it"
    'must': r'\b(mu[-_ ]?st)\b',  # Matches "must", "mu-st", "mu_st" (strict boundary to avoid false positives)
    'netcompany': r'(netcompany(?:[-_ ]\w+)?)',  # Matches "netcompany" and variations like "netcompany-abc", "netcompany_xyz"
    'systematic': r'(systematic(?:[-_ ]\w+)?)',  # Matches "systematic" and variations like "systematic-abc", "systematic_xyz"
    'capgemini': r'(capgemini(?:[-_ ]\w+)?)',  # Matches "capgemini" and variations like "capgemini-abc", "capgemini_xyz"
    'sas institute': r'(sas[-_ ]?institute)',  # Matches "sas institute", "sas_institute", "sas-institute"
    'fellowmind': r'(fellow[-_ ]?mind)',  # Matches "fellowmind", "fellow_mind", "fellow-mind"
    'eg a s': r'\b(eg[-_ ]?a[-_ ]?s|egdw|eg.dk)\b',  # Matches all variations of "eg a s", including "egdw", "eg.dk" (strict boundary)
    'kmd': r'(kmd(?:[-_ ]\w+)?)',  # Matches "kmd" and variations like "kmd-abc", "kmd_xyz"
    'adform': r'(adform)',  # Matches "adform" exactly (no variations needed)
    'oxygen': r'\b(oxygen)\b',  # Matches "oxygen" exactly (no variations needed, strict boundary)
    'saxo bank': r'(saxo[-_ ]?bank)',  # Matches "saxo bank", "saxo_bank", "saxo-bank"
    'kabellmunk': r'(kabellmunk)',  # Matches "kabellmunk" exactly (no variations needed)
    'dgi-it': r'(dgi[-_ ]?it)',  # Matches "dgi-it", "dgi_it", "dgi-it"
    'ørsted': r'(?<!hc)(?<!h\.c\.)(?<!h\.c\. )(?<!h c )(?<!h-c-)(?<!h\. c\. )\b(ørsted|orsted)\b',  # Matches "ørsted" and "orsted", but not "H.C. [øo]rsted"
    'nuuday': r'(nuuday(?:[-_ ]\w+)?)',  # Matches "nuuday" and variations like "nuuday-abc", "nuuday_xyz"
    'yousee': r'(yousee)',  # Matches "yousee" exactly (no variations needed)
    'relatel': r'(relatel(?:[-_ ]\w+)?)',  # Matches "relatel" and variations like "relatel-abc", "relatel_xyz"
    'cphapp': r'(cphapp(?:[-_ ]\w+)?)',  # Matches "cphapp" and variations like "cphapp-abc", "cphapp_xyz"
    'commentor': r'(commentor(?:[-_ ]\w+)?)',  # Matches "commentor" and variations like "commentor-abc", "commentor_xyz"
    'nabto': r'(nabto(?:[-_ ]\w+)?)',  # Matches "nabto" and variations like "nabto-abc", "nabto_xyz"
    'jobindex': r'(jobindex(?:[-_ ]\w+)?)',  # Matches "jobindex" and variations like "jobindex-abc", "jobindex_xyz"
    'miracle': r'(miracle(?:[-_ ]\w+)?)',  # Matches "miracle" and variations like "miracle-abc", "miracle_xyz"
    'immeo': r'(immeo(?:[-_ ]\w+)?)',  # Matches "immeo" and variations like "immeo-abc", "immeo_xyz"
    'siteimprove': r'(siteimprove(?:[-_ ]\w+)?)',  # Matches "siteimprove" and variations like "siteimprove-abc", "siteimprove_xyz"
    'cbrain': r'(cbrain(?:[-_ ]\w+)?)',  # Matches "cbrain" and variations like "cbrain-abc", "cbrain_xyz"
    'deondigital': r'(deon[-_ ]?digital)',  # Matches "deon digital" and "deondigital"
    'pwc': r'(pwc)',  # Matches "pwc" exactly (no variations needed)
    'studiesandme': r'(studiesandme(?:[-_ ]\w+)?)',  # Matches "studiesandme" and variations like "studiesandme-abc", "studiesandme_xyz"
    'tv2': r'(tv2)',  # Matches "tv2" exactly (no variations needed)
    'pentia': r'(pentia(?:[-_ ]\w+)?)',  # Matches "pentia" and variations like "pentia-abc", "pentia_xyz"
    'zervme': r'(zervme(?:[-_ ]\w+)?)',  # Matches "zervme" and variations like "zervme-abc", "zervme_xyz"
    'skat': r'\b(skat)\b',  # Matches "skat" exactly (no variations needed, strict boundary)
    'codefort': r'(codefort(?:[-_ ]\w+)?)',  # Matches "codefort" and variations like "codefort-abc", "codefort_xyz"
    'reepay': r'(reepay(?:[-_ ]\w+)?)',  # Matches "reepay" and variations like "reepay-abc", "reepay_xyz"
    'diviso': r'(diviso(?:[-_ ]\w+)?)',  # Matches "diviso" and variations like "diviso-abc", "diviso_xyz"
    'uni-soft': r'(uni[-_ ]?soft)',  # Matches "uni-soft", "uni_soft", "uni-soft"
    'delegateas': r'(delegateas(?:[-_ ]\w+)?)',  # Matches "delegateas" and variations like "delegateas-abc", "delegateas_xyz"
    'proactivedk': r'(proactivedk(?:[-_ ]\w+)?)',  # Matches "proactivedk" and variations like "proactivedk-abc", "proactivedk_xyz"
    'monstarlab': r'(monstarlab(?:[-_ ]\w+)?)'  # Matches "monstarlab" and variations like "monstarlab-abc", "monstarlab_xyz"
}

