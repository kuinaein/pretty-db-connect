# pretty-db-connect

ケチって EC2 上に DB (PostgreSQL) だけを置くためのスクリプト

## 必要なもの

- Python 3
  - pipenv
- AWS アカウント (要 API アクセスキー)

## 使い方

1. EC2 で[キーペア](https://ap-northeast-1.console.aws.amazon.com/ec2/v2/home?region=ap-northeast-1#KeyPairs)を作成しておく。
1. AWS アクセスキーを取得して `$HOME/.aws/credentials` を設定する。
   - 必要なアクセス権限は[iam-init.json](https://github.com/kuinaein/pretty-db-connect/blob/release/iam-init.json)を参照のこと。
1. CloudFormation で[cloud-fomation.yml](https://github.com/kuinaein/pretty-db-connect/blob/release/cloud-formation.yml)からスタックを作成する。
1. [`pretty_config_exampl.py`](https://github.com/kuinaein/pretty-db-connect/blob/release/pretty_config_example.py)を`pretty_config.py`にコピーし、所要の設定を行う。
1. `pipenv install && pipenv shell && python .\init_precon.py`

## ライセンス

[MIT](https://github.com/kuinaein/pretty-db-connect/blob/release/LICENSE)
