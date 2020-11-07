import os
import sys
import json
import argparse
import zipfile
import requests
from commons.status import *
from jsonschema import validate

sys.path.append('./')
from main import ELM

def elm_manager(mode, database, id, model, app, content, webhook=None):
    # configurazione args per elm
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dataset')
    parser.add_argument('-p', '--preprocess')
    parser.add_argument('-e', '--estimator')
    parser.add_argument('-s', '--selection')
    parser.add_argument('-o', '--output')
    parser.add_argument('--predict')
    parser.add_argument('--store', action="store_true")
    args = parser.parse_args()

    if(mode=='evaluate'):
        # configurazione args per elm in modalità 'evaluate'
        args.dataset = f'{os.getenv("INPUT_PATH")}ds_api.json'
        args.preprocess = f'{os.getenv("INPUT_PATH")}pp_api.json'
        args.estimator = f'{os.getenv("INPUT_PATH")}est_api.json'
        args.selection = f'{os.getenv("INPUT_PATH")}ms_api.json'
        args.output = f'{os.getenv("INPUT_PATH")}output_api.json'
        args.store = True

        app.logger.info("Start training")

        # configurazione e creazione dei file json
        for element in model:
            with open(f'{os.getenv("INPUT_PATH")}{element}_api.json','w') as file:
                json.dump(model[element], file, indent=4)

        # elm start
        try:
            elm = ELM(args)
            elm.process(id)
        except ValueError as error:
            app.logger.error(error)
            # aggiorno il database
            try:
                database.update_one(os.getenv('MODELS_COLLECTION'), {'_id':id}, {'$set':{'status.error':str(err)}})
            except ValueError as error:
                app.logger.error(error)
            return
        
        # creazione zip output
        with zipfile.ZipFile(os.getenv('ZIP_PATH') + '/' + id + '.zip', 'w') as f:
            for root, dirs, files in os.walk(os.getenv('OUTPUT_PATH')):
                for file in files:
                    f.write(os.path.join(root, file))

        # aggiorno il database
        try:
            database.update_one(os.getenv('MODELS_COLLECTION'), {'_id':id}, {'$set':{'status':model_status[4]}})
        except ValueError as error:
            app.logger.error(error)
            return

        app.logger.info("Done training")

        # send webhook
        if webhook:
            app.logger.info(f'Sending status to: {webhook}')
            try:
                requests.get(webhook)
            except:
                app.logger.error("Webhook not send")

    elif(mode=='predict'):
        # configurazione args per elm in modalità 'predict'
        args.predict = f'{os.getenv("INPUT_PATH")}pr_api.json'

        app.logger.info("Start predict")

        # salvataggio del file json
        with open(f'{os.getenv("INPUT_PATH")}pr_api.json','w') as file:
            json.dump(content, file, indent=4)

        # elm start 
        try:
            elm = ELM(args)
            predict = elm.process()
        except ValueError as err:
            app.logger.error(err)
            raise ValueError(err)

        app.logger.info("Done predict")
        return predict