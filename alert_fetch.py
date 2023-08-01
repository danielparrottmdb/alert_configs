try:
    import json
    import sys
    from alert_config import get
except ImportError as e:
  print(e)
  sys.exit(1)

"""
Return a copy of the alert with added metadata ('created', 'updated', etc)
removed.
""" 
def clean_alert(alert):
    new_alert = dict(alert)
    keys = ['created', 'groupId', 'id', 'links', 'updated']
    for k in keys:
        del new_alert[k]
    return new_alert    

def main():
    f = open(sys.path[0] + '/alerts_config.json', 'r')
    iAlertConfig = json.load(f)
    f.close()

    # print(str(iAlertConfig))
    projects = get(baseurl = iAlertConfig['omBaseUrl'], endpoint = '/orgs/' + iAlertConfig['orgID'] + '/groups',
        publicKey = iAlertConfig['publicKey'], privateKey = iAlertConfig['privateKey'], ca_cert_path = iAlertConfig.get('ca_cert_path'))

    # print(str(projects))

    for project in projects['results']:
        print("# Reviewing alerts for %s project\n" % project["name"])
        currentAlerts = get(baseurl = iAlertConfig['omBaseUrl'], endpoint = '/groups/' + project['id'] + '/alertConfigs',
            publicKey = iAlertConfig['publicKey'], privateKey = iAlertConfig['privateKey'], ca_cert_path = iAlertConfig.get('ca_cert_path'))
        jsonAlerts = { "alerts": [ clean_alert(alert) for alert in currentAlerts['results']]}
        print(json.dumps(jsonAlerts, indent=2))

if __name__ == "__main__":
    main()