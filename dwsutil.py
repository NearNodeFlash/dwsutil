#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# DWS Utility runner
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------

import os

from pkg.DWSUtility import DWSUtility

if __name__ == '__main__':
    dwsutility = DWSUtility(os.path.dirname(os.path.normpath(__file__)))
    dwsutility.dump_config_as_json()
    retval = dwsutility.run()
    exit(retval)
