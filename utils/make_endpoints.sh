#!/bin/bash
os=`uname`
echo "changing endpoints to prod"

if [ "$os" = "Darwin" ]
    then
    sed -i "" 's#TWO1_PROD_HOST[[:space:]]*=[[:space:]]*".*"#TWO1_PROD_HOST = "https://dotco-prod-pool2.herokuapp.com"#g' two1/commands/config.py
    sed -i "" 's#TWO1_LOGGER_SERVER[[:space:]]*=[[:space:]]*".*"#TWO1_LOGGER_SERVER = "http://prod-pool-api-logger-2111347410.us-east-1.elb.amazonaws.com"#g' two1/commands/config.py
    sed -i "" 's#TWO1_POOL_URL[[:space:]]*=[[:space:]]*".*"#TWO1_POOL_URL = "swirl+tcp://ac79afc13446427189326683b47d1e7e-803620906.us-east-1.elb.amazonaws.com:21006"#g' two1/commands/config.py
    sed -i "" 's#TWO1_MERCHANT_HOST[[:space:]]*=[[:space:]]*".*"#TWO1_MERCHANT_HOST = "http://two1-merchant-server-prod-1287.herokuapp.com"#g' two1/commands/config.py
else
    sed -i 's#TWO1_PROD_HOST[[:space:]]*=[[:space:]]*".*"#TWO1_PROD_HOST = "https://dotco-prod-pool2.herokuapp.com"#g' two1/commands/config.py
    sed -i 's#TWO1_LOGGER_SERVER[[:space:]]*=[[:space:]]*".*"#TWO1_LOGGER_SERVER = "http://prod-pool-api-logger-2111347410.us-east-1.elb.amazonaws.com"#g' two1/commands/config.py
    sed -i 's#TWO1_POOL_URL[[:space:]]*=[[:space:]]*".*"#TWO1_POOL_URL = "swirl+tcp://ac79afc13446427189326683b47d1e7e-803620906.us-east-1.elb.amazonaws.com:21006"#g' two1/commands/config.py
    sed -i 's#TWO1_MERCHANT_HOST[[:space:]]*=[[:space:]]*".*"#TWO1_MERCHANT_HOST = "http://two1-merchant-server-prod-1287.herokuapp.com"#g' two1/commands/config.py
fi
echo "Finished Changing Endpoints"