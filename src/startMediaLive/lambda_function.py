import json
import boto3
import logging
import os

# The default Lambda Handler
def lambda_handler(event, context):
    # Init Media Live
    live_client = boto3.client('medialive', region_name = os.environ["REGION"])
    
    try:
        body = event["body"]
        ChannelID = body["ChannelID"]

    except KeyError as e:
        return respond(ValueError(str(e)), '[ERROR] Invalid parameters')
    
    state_check = live_client.describe_channel(ChannelId=ChannelID)["State"]
    print(state_check)
    if (state_check == "IDLE") or (state_check == "STOPPING"):
        response = live_client.start_channel(ChannelId=ChannelID)
        
        response_body = {
            "State": response["State"],
            "ChannelID": ChannelID
        }
    
        return respond(None, "Media Live Started successfully", response_body)
    else:
        response_body = {
            "State": state_check,
            "ChannelID": ChannelID
        }
        return respond(None, "Media Live Channel is not available now. Try another channel again...", response_body)

def setup_logger():
    """
    Setup the logger ready to use in your function
    :return: the logger object
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    return logger

def respond(err, user_message=None, response_body=None, respond='application/json'):
    """
    Used for the return of a lambda function to format data suitable for an API gateway response
    :param err: Any error code
    :param user_message: The response to show to the user
    :param response_body: the main response body, usually a dict which is quite large
    :param respond: The response value, can be application/json or text/html
    :return: NONE
    """
    log = setup_logger()
    if err and not user_message:
        user_message = err
        log.error("[400] - {}".format(err))
    elif err:
        log.error("[400] - {} - {}".format(err, user_message))
    else:
        log.info("[200] - {}".format(user_message))

    if 'application/json' in respond:
        return {
            'statusCode': '400' if err else '200',
            'body': json.dumps({'userMessage': str(user_message), 'returnData': str(err) if err else response_body}),
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}
        }
    else:
        return {
            'statusCode': '400' if err else '200',
            'body': {'userMessage': str(user_message), 'returnData': str(err) if err else str(response_body)},
            'headers': {'Content-Type': 'text/html', 'Access-Control-Allow-Origin': '*'}
        }
