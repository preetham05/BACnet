#!/bin/bash

pushd build/html
rsync -avz -e ssh * joelbender,bacpypes@web.sourceforge.net:htdocs/
popd
