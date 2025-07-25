import json
import boto3
import os
import jwt
import datetime
import bcrypt
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])
JWT_SECRET = os.environ['JWT_SECRET']


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def crear_usuario(event, context):
    try:
        body = json.loads(event['body'])
        tenant_id = body['tenant_id']
        username = body['username']
        password = body['password']

        hashed_password = hash_password(password)

        # Evita usuarios duplicados
        table.put_item(
            Item={
                'tenant_id': tenant_id,
                'username': username,
                'password': hashed_password
            },
            ConditionExpression='attribute_not_exists(username)'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Usuario creado exitosamente'})
        }

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 409,
                'body': json.dumps({'message': 'El usuario ya existe'})
            }
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error interno', 'error': str(e)})
        }


def login(event, context):
    try:
        body = json.loads(event['body'])
        tenant_id = body['tenant_id']
        username = body['username']
        password = body['password']

        response = table.get_item(Key={'tenant_id': tenant_id, 'username': username})

        if 'Item' not in response:
            return {'statusCode': 401, 'body': json.dumps({'message': 'Credenciales inválidas'})}

        user = response['Item']

        if not verify_password(password, user['password']):
            return {'statusCode': 401, 'body': json.dumps({'message': 'Credenciales inválidas'})}

        payload = {
            'tenant_id': tenant_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')

        return {
            'statusCode': 200,
            'body': json.dumps({'token': token})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error en login', 'error': str(e)})
        }


def validar_token(event, context):
    token = event['headers'].get('Authorization')

    if not token:
        return {'statusCode': 401, 'body': json.dumps({'message': 'Token requerido'})}

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Token válido', 'payload': payload})
        }

    except jwt.ExpiredSignatureError:
        return {'statusCode': 401, 'body': json.dumps({'message': 'Token expirado'})}

    except jwt.InvalidTokenError:
        return {'statusCode': 401, 'body': json.dumps({'message': 'Token inválido'})}

