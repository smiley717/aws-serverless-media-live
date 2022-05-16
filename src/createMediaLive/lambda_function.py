import boto3
import json
import logging
import os
import uuid

# The default Lambda Handler
def lambda_handler(event, context):
        
	# Init Media Store
	store_client = boto3.client('mediastore', region_name = os.environ["REGION"])
	store_list = store_client.list_containers()
	if (store_list):
		container_info = store_list["Containers"][0]
	else:
		container_info = store_client.create_container(ContainerName = "LiveStreaming")

	container_info["Endpoint"] = container_info["Endpoint"]
	# Init Media Live
	live_client = boto3.client('medialive', region_name = os.environ["REGION"])

	sp_id = str(uuid.uuid4())
	input_name = "input-%s" % sp_id
	
	try:
		# Create input of media live
		live_input = live_client.create_input(
							Name = input_name,
							InputSecurityGroups = ["2380627"],
							Type='RTMP_PUSH',
							Destinations=[
								{
									'StreamName': "live/%s" % sp_id
								},
							],
							)
		print(live_input["Input"]["Id"])
	
		ID = "channel-%s" % sp_id
		input_id = live_input["Input"]["Id"]
		store_creds = container_info["Endpoint"].replace("https", "mediastoressl") + "/%s/index" % sp_id
		
		with open('src/encoder.json') as f:
			data = json.load(f)
		data["OutputGroups"][0]["OutputGroupSettings"]["HlsGroupSettings"]["Destination"]["DestinationRefId"] = ID
		
		roleArn=os.environ["MLROLE"]
	
		response = create_channel(live_client, input_id, store_creds, ID, roleArn, data)

	except KeyError as e:
		return respond(ValueError(str(e)), '[ERROR] Invalid parameters')
	except Exception as e:
		return respond(ValueError(str(e)), '[ERROR] Invalid parameters')
		
	channel_id = response["Channel"]["Id"]
	destination = live_input["Input"]["Destinations"][0]
	server = "rtmp://" + destination["Ip"] + ":" + destination["Port"] + "/live"
	streamKey = sp_id
	
	playBackURL = "https://d3hkklnb15kvc9.cloudfront.net" + "/" + sp_id + "/" + "index.m3u8"
	playHTMLURL = "https://s3.eu-west-2.amazonaws.com/staging.stardm.tv/live_player.html?id=" + sp_id
	
	response_body = {
				"InputID": input_id,
				"ChannelID": channel_id,
				"Server": server,
				"StreamKey": streamKey,
				"PlaybackURL":playBackURL,
				"PlayHTMLURL":playHTMLURL
	}
	
	return respond(None, "Media Live got successfully", response_body)

def create_channel(client, input_id, destination, ID, arn, data):
	response = client.create_channel(
		ChannelClass="SINGLE_PIPELINE",
		Destinations=[
		 {
			 'Id': ID,
			 'Settings': [
				{
					 'Url': destination,
				},
			 ]
		 }],
		InputAttachments=[{
			"InputId": input_id
		}],
		EncoderSettings=data,
		Name=ID,
		RoleArn=arn)
	return response

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
