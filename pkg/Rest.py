# -*- coding: utf-8 -*-
#
# Copyright 2021, 2022 Hewlett Packard Enterprise Development LP
# Other additional copyright holders may be indicated within.
#
# The entirety of this work is licensed under the Apache License,
# Version 2.0 (the "License"); you may not use this file except
# in compliance with the License.
#
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# DWS Utility Configuration Class

import requests
import json
from .Console import Console


class Response:
    def __init__(self, response):
        self.response = response
        self.json = self.response.json()

    def http_status_code(self):
        return self.response.status_code

    def successful(self):
        return self.http_status_code() >= 200 and self.http_status_code() < 300

    def dump_json(self):
        print(json.dumps(self.json))
        # data = r.json()
        # #print("JSON: "+json.dumps(data))
        # Console.debug(Console.TRACE, msg)


class Request:
    def construct_base_url(protocol, host, port):
        return f"{protocol}://{host}:{port}/"

    def __init__(self, protocol, host, port, headers={}):
        self.protocol = protocol
        self.host = host
        self.port = port
        self.headers = headers
        self.base_url = f"{self.protocol}://{self.host}:{self.port}/"

    def full_url(self, path):
        return f"{self.base_url}{path}"

    def full_headers(self, headers):
        hdrs = self.headers.copy()
        if headers is not None:
            hdrs.update(headers)
        return hdrs

    def post(self, path, body, headers={}):
        url = self.full_url(path)
        hdrs = self.full_headers(headers)
        hdrs = {**hdrs, "Content-Type": "application/json"}
        Console.debug(Console.WORDY, f"POST {url}, body={body}, headers={hdrs}")
        return Response(requests.post(url, body, headers=hdrs))

    def put(self, path, body, headers={}):
        url = self.full_url(path)
        hdrs = self.full_headers(headers)
        hdrs = {**hdrs, "Content-Type": "application/json-patch+json"}
        Console.debug(Console.WORDY, f"PUT {url}, body={body}, headers={hdrs}")
        return Response(requests.put(url, body, headers=hdrs))

    def get(self, path, headers={}):
        url = self.full_url(path)
        hdrs = self.full_headers(headers)
        Console.debug(Console.WORDY, f"GET {url}, headers={hdrs}")
        return Response(requests.get(url, headers=hdrs))

    def patch(self, path, body, headers={}):
        url = self.full_url(path)+"?fieldManager=kubectl-patch"
        hdrs = self.full_headers(headers)
        hdrs = {**hdrs, "Content-Type": "application/json-patch+json"}
        Console.debug(Console.WORDY, f"PATCH {url}, body={body}, headers={hdrs}")
        resp = Response(requests.patch(url, body, headers=hdrs))
        Console.debug(Console.WORDY, "http status code: {0}".format(resp.http_status_code()))
        return resp

        # r = requests.get('http://192.168.100.12:8080/apis/dws.cray.hpe.com/v1alpha1/namespaces/default/workflows/')
        # print(f"HTTP Status: {r.status_code}")
        # print(f"text: {r.text}")
        # print(f"json: {r.json()}")

        # if r.status_code == 200:
        # data = r.json()
        # #print("JSON: "+json.dumps(data))
        # print(f"apiVersion: {data['apiVersion']}")

# kubectl -v=8 patch workflows.dws.cray.hpe.com wfr-2941 --type='json' -p='[{"op":"replace", "path":"/spec/desiredState", "value":"setup"}]'
# I0823 22:09:25.413818 1057477 request.go:1123] Request Body: [{"op":"replace","path":"/spec/desiredState","value":"setup"}]
# I0823 22:09:25.414464 1057477 round_trippers.go:432] PATCH https://127.0.0.1:43349/apis/dws.cray.hpe.com/v1alpha1/namespaces/default/workflows/wfr-2941?fieldManager=kubectl-patch
# I0823 22:09:25.414477 1057477 round_trippers.go:438] Request Headers:
# I0823 22:09:25.414482 1057477 round_trippers.go:442]     Content-Type: application/json-patch+json
# I0823 22:09:25.414489 1057477 round_trippers.go:442]     Accept: application/json
# I0823 22:09:25.414493 1057477 round_trippers.go:442]     User-Agent: kubectl/v1.21.2 (linux/amd64) kubernetes/092fbfb
# I0823 22:09:25.515248 1057477 round_trippers.go:457] Response Status: 200 OK in 100 milliseconds
# I0823 22:09:25.515271 1057477 round_trippers.go:460] Response Headers:
# I0823 22:09:25.515276 1057477 round_trippers.go:463]     Cache-Control: no-cache, private
# I0823 22:09:25.515280 1057477 round_trippers.go:463]     Content-Type: application/json
# I0823 22:09:25.515283 1057477 round_trippers.go:463]     X-Kubernetes-Pf-Flowschema-Uid: 165f9f75-f7d1-4526-97e7-c814a9fdc181
# I0823 22:09:25.515286 1057477 round_trippers.go:463]     X-Kubernetes-Pf-Prioritylevel-Uid: b1b84f85-dc34-4d0b-91c6-ba00b21d2174
# I0823 22:09:25.515289 1057477 round_trippers.go:463]     Content-Length: 1565
# I0823 22:09:25.515293 1057477 round_trippers.go:463]     Date: Mon, 23 Aug 2021 22:09:25 GMT
# I0823 22:09:25.515316 1057477 request.go:1123] Response Body: {"apiVersion":"dws.cray.hpe.com/v1alpha1","kind":"Workflow","metadata":{"creationTimestamp":"2021-08-23T21:34:59Z","generation":7,"managedFields":[{"apiVersion":"dws.cray.hpe.com/v1alpha1","fieldsType":"FieldsV1","fieldsV1":{"f:spec":{".":{},"f:dwDirectives":{},"f:jobID":{},"f:userID":{},"f:wlmID":{}}},"manager":"python-requests","operation":"Update","time":"2021-08-23T21:34:59Z"},{"apiVersion":"dws.cray.hpe.com/v1alpha1","fieldsType":"FieldsV1","fieldsV1":{"f:spec":{"f:desiredState":{}}},"manager":"kubectl-patch","operation":"Update","time":"2021-08-23T21:53:25Z"},{"apiVersion":"dws.cray.hpe.com/v1alpha1","fieldsType":"FieldsV1","fieldsV1":{"f:status":{"f:message":{},"f:ready":{},"f:reason":{},"f:state":{}}},"manager":"dws-operator","operation":"Update","time":"2021-08-23T21:53:26Z"}],"name":"wfr-2941","namespace":"default","resourceVersion":"1926698","uid":"28b3a336-2308-4301-95d1-5affb726d979"},"spec":{"desiredState":"setup","dwDirectives":["#DW jobdw type=xfs capacity=10GB name=test-99"],"jobID":2941,"use [truncated 541 chars]
# workflow.dws.cray.hpe.com/wfr-2941 patched
