#!/bin/bash

cd Preprocessing

# step1 fetch video from youtube
python Preprocessing/fetch_video.py --config Preprocessing/acc_config/style_show.yaml --output Preprocessing/output_batch/style_show.xlsx

# step2 执行主处理流程
cd ../Videolingo
python -m batch.utils.batch_processor --excel ../Preprocessing/output_batch/style_show.xlsx


# step3 进行后处理

cd ../Post_processing

python uploader.py

# step4 进行上传

biliup -u style.json upload -c style/config_bili.yaml


