import requests
import json

def get_clusters():
    api_url = "https://rancher.wpnops.com"
    api_token = "token-j6p65:qtqtg6hfqqtcd874ns69rkvkgpq482hbsgtx6b2hggv479cjrgjmr9"
    cluster_id = "c-m4rkn"
    registration_token_url ="{}{}{}{}".format(api_url, "/v3/clusters/", cluster_id, "/clusterregistrationtoken")
    print(registration_token_url)
    registration_data = '{"type": "clusterRegistrationToken", "clusterId": "c-m4rkn"}'
    print(registration_data)
    requests.put(registration_token_url, data=registration_data, auth=BearerAuth(api_token))


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r

get_clusters()