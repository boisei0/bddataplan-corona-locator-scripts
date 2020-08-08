from collections import defaultdict

import requests
import datetime

gemeente_to_veiligheidsregio_url = 'https://raw.githubusercontent.com/minvws/nl-covid19-data-dashboard/develop/src/data/gemeente_veiligheidsregio.json'


def prepare_gemeente_lookup_table():
    _gemeente_lookup_table = requests.get(gemeente_to_veiligheidsregio_url).json()

    # Onderstaande code geschreven onder invloed van pijnstilling; verbetering voor deze lelijke hack is bijzonder welkom
    gemeente_lookup_table = defaultdict(list)
    for gemeente, vrcode in _gemeente_lookup_table.items():
        _gemeente_data_obj = {'vrcode': vrcode}

        if '(' in gemeente:
            gemeente_parts = gemeente.split('(')
            _gemeente = gemeente_parts[0].strip()
            if gemeente_parts[1] == 'gemeente)':
                if _gemeente == 's-Gravenhage':  # Serieus waarom VWS?
                    _gemeente = "'s-Gravenhage"
                gemeente_lookup_table[_gemeente].append(_gemeente_data_obj)
            else:
                # Provincie, voeg veld toe voor lookup
                if gemeente_parts[1] == 'L.)':
                    _gemeente_data_obj['province'] = 'Limburg'
                elif gemeente_parts[1] == 'NH.)':
                    _gemeente_data_obj['province'] = 'Noord-Holland'
                elif gemeente_parts[1] == 'Z.)':
                    _gemeente_data_obj['province'] = 'Zeeland'
                elif gemeente_parts[1] == 'ZH.)':
                    _gemeente_data_obj['province'] = 'Zuid-Holland'
                elif gemeente_parts[1] == 'O.)':
                    _gemeente_data_obj['province'] = 'Overijssel'
                else:
                    raise NotImplementedError(f'Gemeente gevonden in bijzondere vorm: {gemeente}; graag toevoegen aan de code.')

                gemeente_lookup_table[_gemeente].append(_gemeente_data_obj)

        else:
            if gemeente == 's-Hertogenbosch':
                gemeente = "'s-Hertogenbosch"  # VWS serieus waarom?
            gemeente_lookup_table[gemeente].append({'vrcode': vrcode})
    return gemeente_lookup_table


# Vrij naar: https://raw.githubusercontent.com/minvws/nl-covid19-data-dashboard/develop/src/data/index.ts
vr_lookup_table = {
    'VR01': 'Groningen',
    'VR02': 'Friesland',
    'VR03': 'Drenthe',
    'VR04': 'IJsselland',
    'VR05': 'Twente',
    'VR06': 'Noord- en Oost-Gelderland',
    'VR07': 'Gelderland-Midden',
    'VR08': 'Gelderland-Zuid',
    'VR09': 'Utrecht',
    'VR10': 'Noord-Holland Noord',
    'VR11': 'Zaanstreek-Waterland',
    'VR12': 'Kennemerland',
    'VR13': 'Amsterdam-Amstelland',
    'VR14': 'Gooi en Vechtstreek',
    'VR15': 'Haaglanden',
    'VR16': 'Hollands Midden',
    'VR17': 'Rotterdam-Rijnmond',
    'VR18': 'Zuid-Holland Zuid',
    'VR19': 'Zeeland',
    'VR20': 'Midden- en West-Brabant',
    'VR21': 'Brabant-Noord',
    'VR22': 'Brabant-Zuidoost',
    'VR23': 'Limburg-Noord',
    'VR24': 'Zuid-Limburg',
    'VR25': 'Flevoland',
}

data_veiligheidsregio_url = 'https://coronadashboard.rijksoverheid.nl/json/{vrcode}.json'
data_rivm_url = 'https://data.rivm.nl/covid-19/COVID-19_aantallen_gemeente_cumulatief.json'

def get_corona_dashboard_data():
    # Data volgens coronadashboard (ziekenhuisopnames):
    DATA_VR_ZIEKENHUIS_PER_DAG_CD = defaultdict(dict)

    for vrcode in vr_lookup_table.keys():
        data = requests.get(data_veiligheidsregio_url.format(vrcode=vrcode)).json()
        for dag_data in data['intake_hospital_ma']['values']:
            datum = datetime.datetime.fromtimestamp(dag_data['date_of_report_unix']).strftime('%Y-%m-%d')
            DATA_VR_ZIEKENHUIS_PER_DAG_CD[vrcode][datum] = dag_data['intake_hospital_ma']
    return DATA_VR_ZIEKENHUIS_PER_DAG_CD


def get_rivm_data_cumulatief():
    # Data volgens RIVM (ziekenhuisopnames):
    data_cumulatief = defaultdict(dict)

    rivm_data = requests.get(data_rivm_url).json()
    gemeente_lookup_table = prepare_gemeente_lookup_table()

    for report in rivm_data:
        if report['Municipality_name'] is None:
            continue

        if '(' in report['Municipality_name']:
            # bah
            gemeente = report['Municipality_name'].split('(')[0].strip()
        else:
            gemeente = report['Municipality_name']

        gemeente_info = gemeente_lookup_table[gemeente]
        if len(gemeente_info) > 1:
            # Meerdere opties verspreid over provincies
            gemeente_info = list(filter(lambda x: x['province'] == report['Province'], gemeente_info))[0]
        else:
            gemeente_info = gemeente_info[0]

        # En dan nu data schrapen:
        datum = report['Date_of_report'].split(' ')[0]
        if datum not in data_cumulatief[gemeente_info['vrcode']]:
            data_cumulatief[gemeente_info['vrcode']][datum] = 0
        data_cumulatief[gemeente_info['vrcode']][datum] += report['Hospital_admission']

    return data_cumulatief


def get_rivm_data_dagelijks_verschil(data_cumulatief):
    data_dagelijks_verschil = defaultdict(dict)

    for vrcode in data_cumulatief.keys():
        datums = sorted(data_cumulatief[vrcode].keys())
        for i, datum in enumerate(datums[1:], start=1):
            data_dagelijks_verschil[vrcode][datum] = \
                data_cumulatief[vrcode][datum] - data_cumulatief[vrcode][datums[i - 1]]

    return data_dagelijks_verschil


def get_rivm_data_dagelijks_opgenomen(data_dagelijks_verschil):
    data = defaultdict(dict)

    for vrcode in data_dagelijks_verschil.keys():
        for datum in data_dagelijks_verschil[vrcode].keys():
            val = data_dagelijks_verschil[vrcode][datum]
            data[vrcode][datum] = 0 if val < 0 else val

    return data


def get_rivm_data_3day_avg(data_dagelijks):
    data_3day_avg = defaultdict(dict)

    for vrcode in data_dagelijks.keys():
        datums = sorted(data_dagelijks[vrcode].keys())
        for i, datum in enumerate(datums[2:], start=2):
            data_3day_avg[vrcode][datum] = \
                float(format((data_dagelijks[vrcode][datum] +
                 data_dagelijks[vrcode][datums[i - 1]] +
                 data_dagelijks[vrcode][datums[i - 2]]) / 3.0, '.1f'))  # netjes afronden op 1 decimaal zonder al te rare fratsen

    return data_3day_avg


rivm_cumulatief = get_rivm_data_cumulatief()
rivm_dagelijks_verschil = get_rivm_data_dagelijks_verschil(rivm_cumulatief)
rivm_3day_avg = get_rivm_data_3day_avg(rivm_dagelijks_verschil)
rivm_3day_avg_opgenomen = get_rivm_data_3day_avg(get_rivm_data_dagelijks_opgenomen(rivm_dagelijks_verschil))

cd = get_corona_dashboard_data()

print('[*] Voor veiligheidsregio NOG, op 2020-07-16:')
print(f"[+] Gemiddelde op basis cumulatief RIVM: {rivm_3day_avg['VR06']['2020-07-16']}")
print(f"[+] Gemiddelde op basis cumulatief RIVM, maar dag < 0 => dag = 0: {rivm_3day_avg_opgenomen['VR06']['2020-07-16']}")
print(f"[+] Gemiddelde van Corona Dashboard: {cd['VR06']['2020-07-16']}")


for vrcode in rivm_3day_avg.keys():
    for datum in rivm_3day_avg[vrcode]:
        if rivm_3day_avg_opgenomen[vrcode][datum] != cd[vrcode][datum]:
            print(f"Discrepantie bij {vr_lookup_table[vrcode]} op {datum}; RIVM: {rivm_3day_avg_opgenomen[vrcode][datum]}, CoronaDashboard: {cd[vrcode][datum]}")
