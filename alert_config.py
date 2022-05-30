try:
  import requests
  import json
  import os
  import sys
  from requests.auth import HTTPDigestAuth
except ImportError as e:
  print(e)
  sys.exit(1)
 
# /
  # Function to determine if correct alerts exist and add if they donot.
  # Also modify alerts if they are incorrect
  #
  # Inputs:
  #   currentAlerts:  The alerts list as returned by the Ops Manager API
  #   desiredAlerts: An array alerts to comapre against that have desired attributes.
# /
def checkAlerts(currentAlerts, desiredAlerts):
  # alert settings to check
  checkKeys = [ 'eventTypeName', 'matchers', 'notifications', 'threshold', 'typeName', 'metricThreshold' ]
  newAlerts = []
  updateAlerts = []
  groupId = currentAlerts[0]['groupId']
  replaceAlert = False
 
  if len(desiredAlerts) > 0:
    for desiredAlert in desiredAlerts:
      if any((currentAlert['eventTypeName'] == desiredAlert['eventTypeName'] and 
        (currentAlert['eventTypeName'] != 'OUTSIDE_METRIC_THRESHOLD' or 
        (currentAlert['eventTypeName'] == 'OUTSIDE_METRIC_THRESHOLD' and
        currentAlert['metricThreshold']['metricName'] == desiredAlert['metricThreshold']['metricName']))) for currentAlert in currentAlerts):
          alert = [i for i in currentAlerts 
            if (i['eventTypeName'] == desiredAlert['eventTypeName'] and 
            (i['eventTypeName'] != 'OUTSIDE_METRIC_THRESHOLD') or 
            (i['eventTypeName'] == 'OUTSIDE_METRIC_THRESHOLD' and 
            'metricThreshold' in i and 
            'metricThreshold' in desiredAlert and 
            i['metricThreshold']['metricName'] == desiredAlert['metricThreshold']['metricName']))]
          if len(alert) > 0:
            for k in checkKeys:
              if k in desiredAlert:
                if json.dumps(alert[0][k], sort_keys = True) != json.dumps(desiredAlert[k], sort_keys = True):
                  print("Alert needs modifying: %s current %s desired %s" % (alert[0]['id'], alert[0][k], desiredAlert[k]))
                  updateAlerts.append(dict({'id': alert[0]['id']}, **desiredAlert))
                  replaceAlert = True
                  break
      else:
        desiredAlert['groupId'] = groupId
        newAlerts.append(desiredAlert)
        replaceAlert = True
 
  return replaceAlert,newAlerts,updateAlerts
 
# /
  # get function to perform GET a payload to a REST API endpoint over HTTPS
  #
  # Inputs:
  #   baseurl: The URL for Ops Manager, including the base API, e.g. `htts://ops-manager.gov.au:8443/api/public/v1.0`
  #   endpoint: The desired endpoint starting with a slash, e.g. `/groups/{PROJECT-ID}/automationConfig`
  #   ca_cert_path: The absolute path, including file name, of the CA certificate
  #   privateKey: The private key portion of the Ops Manager API Access Key
  #   publicKey: The public key portion of the Ops Manager API Access Key
  #   key: The absolute path to the combined private key and X.509 certificate. OPTIONAL
# /
def get(baseurl, endpoint, ca_cert_path, privateKey, publicKey, key = None):
  resp = requests.get(baseurl.rstrip('/') + endpoint, auth = HTTPDigestAuth(publicKey, privateKey), verify = ca_cert_path, cert = key, timeout = 10)
  if resp.status_code == 200:
    group_data = json.loads(resp.text)
    return group_data
  else:
    print("""\033[91mERROR!\033[0;0m GET response was %s, not `200`\033[m""" % resp.status_code)
    print(resp.text)
    raise requests.exceptions.RequestException
 
# /
  # put function to perform PUT a payload to a REST API endpoint over HTTPS
  #
  # Inputs:
  #   baseurl: The URL for Ops Manager, including the base API, e.g. `htts://ops-manager.gov.au:8443/api/public/v1.0`
  #   endpoint: The desired endpoint starting with a slash, e.g. `/groups/{PROJECT-ID}/automationConfig`
  #   data: JSON paylod to upload
  #   ca_cert_path: The absolute path, including file name, of the CA certificate
  #   privateKey: The private key portion of the Ops Manager API Access Key
  #   publicKey: The public key portion of the Ops Manager API Access Key
  #   key: The absolute path to the combined private key and X.509 certificate. OPTIONAL
# /
def put(baseurl, endpoint, data, ca_cert_path, privateKey, publicKey, key = None):
  header = {'Content-Type': 'application/json'}
  # Attempt three times if we have contention
  for i in range(0,2):
    while True:
      resp = requests.put(baseurl.rstrip('/') + endpoint, auth=HTTPDigestAuth(publicKey, privateKey), verify = ca_cert_path, cert = key, timeout = 10, data = json.dumps(data), headers = header)
      if resp.status_code == 200:
        return resp
      elif resp.status_code == 409:
        print("Contention issues: %s" % resp.text)
        sleep(randint(1,5))
        continue
      else:
        print("""\033[91mERROR!\033[0;0m PUT response was %s, not `200`\033[m""" % resp.status_code)
        print(resp.text)
        raise requests.exceptions.RequestException
 
# /
  # post function to perform POST a payload to a REST API endpoint over HTTPS
  #
  # Inputs:
  #   baseurl: The URL for Ops Manager, including the base API, e.g. `htts://ops-manager.gov.au:8443/api/public/v1.0`
  #   endpoint: The desired endpoint starting with a slash, e.g. `/groups/{PROJECT-ID}/automationConfig`
  #   data: JSON paylod to upload
  #   ca_cert_path: The absolute path, including file name, of the CA certificate
  #   privateKey: The private key portion of the Ops Manager API Access Key
  #   publicKey: The public key portion of the Ops Manager API Access Key
  #   key: The absolute path to the combined private key and X.509 certificate. OPTIONAL
# /
def post(baseurl, endpoint, data, ca_cert_path, privateKey, publicKey, key = None):
  header = {'Content-Type': 'application/json'}
  # Attempt three times if we have contention
  for i in range(0,2):
    while True:
      resp = requests.post(baseurl.rstrip('/') + endpoint, auth=HTTPDigestAuth(publicKey, privateKey), verify = ca_cert_path, cert = key, timeout = 10, data = json.dumps(data), headers = header)
      if resp.status_code == 200 or resp.status_code == 201:
        return resp
      elif resp.status_code == 409:
        print("Contention issues: %s" % resp.text)
        sleep(randint(1,5))
        continue
      else:
        print("""\033[91mERROR!\033[0;0m POST response was %s, not `200`\033[m""" % resp.status_code)
        print(resp.text)
        raise requests.exceptions.RequestException
 
def main():
  # load config file
  if not os.path.isfile(sys.path[0] + '/alerts_config.json'):
    raise Exception("""
\033[1;31mERROR!\033[0;0m The config file `alerts_config.json` must exist in the same directory as the Python script
The config file must contain the following:
{
  "omBaseUrl": "https://<OPS_MANAGER_ADDRESS>:<OPS_MANAGER_PORT>/api/public/v1.0",
  "orgID": "<ID_OF_THE_OPS_MANAGER_ORGANISATION",
  "ca_cert_path": "<ABSOLUTE_PATH_OF_CA_CERT",
  "publicKey": "<OPS_MANAGER_API_PUBLIC_KEY",
  "privateKey": "OPS_MANAGER_API_PRIVATE_KEY"
}
 
The `publicKey` and `privateKey` combination MUST have Org-level write permssions.
    """)
  f = open(sys.path[0] + '/alerts_config.json', 'r')
  iAlertConfig = json.load(f)
  f.close()
 
  # load desired alerts
  if not os.path.isfile(sys.path[0] + '/desired_alerts.json'):
    raise Exception("""
\033[1;31mERROR!\033[0;0m A JSON file must exist called `desired_alerts.json` in the same directory as the script.
The file must contain a key called `alerts` which is an array of desired alert objects""")
  a = open(sys.path[0] + '/desired_alerts.json','r')
  iAlertConfig['requiredAlerts'] = json.load(a)['alerts']
 
  projects = get(baseurl = iAlertConfig['omBaseUrl'], endpoint = '/orgs/' + iAlertConfig['orgID'] + '/groups',
    publicKey = iAlertConfig['publicKey'], privateKey = iAlertConfig['privateKey'], ca_cert_path = iAlertConfig['ca_cert_path'])
 
  for project in projects['results']:
    print("Reviewing alerts for %s project\n" % project["name"])
    currentAlerts = get(baseurl = iAlertConfig['omBaseUrl'], endpoint = '/groups/' + project['id'] + '/alertConfigs',
    publicKey = iAlertConfig['publicKey'], privateKey = iAlertConfig['privateKey'], ca_cert_path = iAlertConfig['ca_cert_path'])
 
    replaceAlerts,newAlerts,updateAlerts = checkAlerts(currentAlerts['results'], iAlertConfig['requiredAlerts'])
 
    print("Alerts for %s: New: \033[1;32m%s\033[0;0m, Updates: \033[1;36m%s\033[0;0m" % (project['id'], len(newAlerts), len(updateAlerts)))
 
    if replaceAlerts:
      if newAlerts:
        for alert in newAlerts:
          print("\033[1;32mNew alert!\033[0;0m: %s" % alert)
          result = post(baseurl = iAlertConfig['omBaseUrl'], endpoint = '/groups/' + project['id'] + '/alertConfigs',
            publicKey = iAlertConfig['publicKey'], privateKey = iAlertConfig['privateKey'], ca_cert_path = iAlertConfig['ca_cert_path'], data = alert)
          print(result)
      if updateAlerts:
        for alert in updateAlerts:
          print("\033[1;36mNew alert!\033[0;0m: %s" % alert)
          result = put(baseurl = iAlertConfig['omBaseUrl'], endpoint = '/groups/' + project['id'] + '/alertConfigs/' + alert['id'],
            publicKey = iAlertConfig['publicKey'], privateKey = iAlertConfig['privateKey'], ca_cert_path = iAlertConfig['ca_cert_path'], data = alert)
          print(result)
 
if __name__ == "__main__": main()
