""" PagerMaid module to handle sticker collection. """

from PIL import Image
from os.path import exists
from os import remove
from requests import get
from random import randint
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import MessageEntityMentionName
from telethon.errors.rpcerrorlist import ChatSendStickersForbiddenError
from struct import error as StructError
from pagermaid.listener import listener
from pagermaid.utils import alias_command
from pagermaid import redis, config
from collections import defaultdict
import json


try:
    git_source = config['git_source']
except:
    git_source = "https://raw.githubusercontent.com/Xtao-Labs/PagerMaid_Plugins/master/"
positions = {
    "1": [14, 267],
    "2": [97, 14],
    "3": [60, 221],
    "4": [63, 379],
    "5": [291, 202],
    "6": [243, 55],
    "7": [31, 191],
    "8": [22, 338],
    "9": [42, 142],
    "10": [31, 187],
    "11": [133, 209],
}
notifyStrArr = {}
max_number = len(positions)
configFilePath = 'plugins/shark/config.json'
configFileRemoteUrlKey = "shark.configFileRemoteUrl"


async def shark_it(context, base, mask, photo, number, layer = 0):
    mask_size = mask.size
    photo_size = photo.size
    if mask_size[0] < photo_size[0] and mask_size[1] < photo_size[1]:
        scale = photo_size[1] / mask_size[1]
        photo = photo.resize((int(photo_size[0] / scale), int(photo_size[1] / scale)), Image.LANCZOS)
    photo = photo.crop((0, 0, mask_size[0], mask_size[1]))
    mask1 = Image.new('RGBA', mask_size)
    mask1.paste(photo, mask=mask)
    numberPosition = positions[str(number)]
    base.paste(mask1, (numberPosition[0], numberPosition[1]), mask1)

    # 增加判断是否有第二个头像孔
    isContinue = len(numberPosition) > 2 and layer == 0
    if isContinue:
        await context.client.download_profile_photo(
            from_user.user.id,
            "plugins/shark/" + str(from_user.user.id) + ".jpg",
            download_big=True
        )
        try:
            markImg = Image.open("plugins/shark/" + str(from_user.user.id) + ".jpg")
            maskImg = Image.open("plugins/shark/mask" + str(numberPosition[2]) + ".png")
        except:
            await context.edit(f"图片模版加载出错，请检查并更新配置：mask{str(numberPosition[2])}.png")
            return base
        base = await shark_it(context, base, maskImg, markImg, numberPosition[2], layer+1)

    temp = base.size[0] if base.size[0] > base.size[1] else base.size[1]
    if temp != 512:
        scale = 512 / temp
        base = base.resize((int(base.size[0] * scale), int(base.size[1] * scale)), Image.LANCZOS)

    return base


async def updateConfig(configFilePath, context):
    configFileRemoteUrl = redis.get(configFileRemoteUrlKey)
    if configFileRemoteUrl:
        if downloadFileFromUrl(configFileRemoteUrl, configFilePath) != 0:
            redis.set(configFileRemoteUrlKey, configFileRemoteUrl)
            return -1
        else:
            return await loadConfigFile(configFilePath, context, True)
    return 0


def downloadFileFromUrl(url, filepath):
    try:
        re = get(url)
        with open(filepath, 'wb') as ms:
            ms.write(re.content)
    except:
        return -1
    return 0


async def loadConfigFile(configFilePath, context, forceDownload = False):
    global positions, notifyStrArr
    try:
        with open(configFilePath, 'r', encoding='utf8') as cf:
            # 读取已下载的配置文件
            remoteConfigJson = json.load(cf)
            # positionsStr = json.dumps(positions)
            # positions = json.loads(positionsStr)

            # 读取配置文件中的positions
            positionsStr = json.dumps(remoteConfigJson["positions"])
            data = json.loads(positionsStr)
            # 与预设positions合并
            positions = mergeDict(positions, data)

            # 读取配置文件中的notifies
            data = json.loads(json.dumps(remoteConfigJson["notifies"]))
            # 与预设positions合并
            notifyStrArr = mergeDict(notifyStrArr, data)

            # 读取配置文件中的needDownloadFileList
            data = json.loads(json.dumps(remoteConfigJson["needDownloadFileList"]))
            # 下载列表中的文件
            for fileurl in data:
                try:
                    fsplit = fileurl.split("/")
                    filePath = f"plugins/shark/{fsplit[len(fsplit)-1]}"
                    if not exists(filePath) or forceDownload:
                        downloadFileFromUrl(fileurl, filePath)

                except:
                    await context.edit(f"下载文件异常，url：{fileurl}")
                    return -1
    except:
        return -1
    return 0


def mergeDict(d1, d2):
    dd = defaultdict(list)

    for d in (d1, d2):
        for key, value in d.items():
            dd[key] = value
    return dict(dd)


@listener(is_plugin=True, outgoing=True, command=alias_command("shark"),
          description="生成一张 🦈🦈 图片\n"
                      "可选：当第二个参数是数字时，读取预存的配置；\n\n"
                      "当第二个参数是.开头时，头像旋转180°，并且判断r后面是数字则读取对应的配置生成\n\n"
                      "当第二个参数是/开头时，在/后面加url则从url下载配置文件保存到本地，如果就一个/，则直接更新配置文件，删除则是/delete\n\n"
                      "当第二个参数是-开头时，在d后面加上模版id，即可设置默认模版-shark直接使用该模版，删除默认模版是-shark -\n\n"
                      "当第二个参数是!或者！开头时，列出当前可用模版",
          parameters="<username/uid> [随意内容]")
async def shark(context):
    if len(context.parameter) > 2:
        await context.edit("出错了呜呜呜 ~ 无效的参数。")
        return
    diu_round = False
    user_object = await context.client.get_me()
    global from_user
    from_user = await context.client(GetFullUserRequest(user_object.id))
    if context.reply_to_msg_id:
        reply_message = await context.get_reply_message()
        try:
            user_id = reply_message.sender_id
        except AttributeError:
            await context.edit("出错了呜呜呜 ~ 无效的参数。")
            return
        target_user = await context.client(GetFullUserRequest(user_id))
    else:
        if len(context.parameter) == 1 or len(context.parameter) == 2:
            user = context.parameter[0]
            if user.isnumeric():
                user = int(user)
        else:
            user = user_object.id
        if context.message.entities is not None:
            if isinstance(context.message.entities[0], MessageEntityMentionName):
                return await context.client(GetFullUserRequest(context.message.entities[0].user_id))
        try:
            user_object = await context.client.get_entity(user)
            target_user = await context.client(GetFullUserRequest(user_object.id))
        except (TypeError, ValueError, OverflowError, StructError) as exception:
            if str(exception).startswith("Cannot find any entity corresponding to"):
                await context.edit("出错了呜呜呜 ~ 指定的用户不存在。")
                return
            if str(exception).startswith("No user has"):
                await context.edit("出错了呜呜呜 ~ 指定的道纹不存在。")
                return
            if str(exception).startswith("Could not find the input entity for") or isinstance(exception, StructError):
                await context.edit("出错了呜呜呜 ~ 无法通过此 UserID 找到对应的用户。")
                return
            if isinstance(exception, OverflowError):
                await context.edit("出错了呜呜呜 ~ 指定的 UserID 已超出长度限制，您确定输对了？")
                return
            raise exception
    photo = await context.client.download_profile_photo(
        target_user.user.id,
        "plugins/shark/" + str(target_user.user.id) + ".jpg",
        download_big=True
    )

    reply_to = context.message.reply_to_msg_id
    if exists("plugins/shark/" + str(target_user.user.id) + ".jpg"):
        for num in range(1, max_number + 1):
            print(num)
            if not exists('plugins/shark/shark' + str(num) + '.png'):
                re = get('https://raw.githubusercontent.com/fishingworld/PagerMaid_Plugins/master/shark/shark' + str(num) + '.png')
                with open('plugins/shark/shark' + str(num) + '.png', 'wb') as bg:
                    bg.write(re.content)
            if not exists('plugins/shark/mask' + str(num) + '.png'):
                re = get('https://raw.githubusercontent.com/fishingworld/PagerMaid_Plugins/master/shark/mask' + str(num) + '.png')
                with open('plugins/shark/mask' + str(num) + '.png', 'wb') as ms:
                    ms.write(re.content)
        number = randint(1, max_number)
        try:
            p1 = 0
            p2 = 0
            if len(context.parameter) == 1:
                p1 = context.parameter[0]
                if p1[0] == ".":
                    diu_round = True
                    if len(p1) > 1:
                        try:
                            p2 = int("".join(p1[1:]))
                        except:
                            # 可能也有字母的参数
                            p2 = "".join(p1[1:])
                elif p1[0] == "-":
                    if len(p1) > 1:
                        try:
                            p2 = int("".join(p1[1:]))
                        except:
                            # 可能也有字母的参数
                            p2 = "".join(p1[1:])
                    if p2:
                        redis.set("shark.default-config", p2)
                        await context.edit(f"已经设置默认配置为：{p2}")
                    else:
                        redis.delete("shark.default-config")
                        await context.edit(f"已经清空默认配置")
                    return
                elif p1[0] == "/":
                    await context.edit(f"正在更新远程配置文件")
                    if len(p1) > 1:
                        # 获取参数中的url
                        p2 = "".join(p1[1:])
                        if p2 == "delete":
                            redis.delete(configFileRemoteUrlKey)
                            await context.edit(f"已清空远程配置文件url")
                            return
                        # 下载文件
                        if downloadFileFromUrl(p2, configFilePath) != 0:
                            await context.edit(f"下载配置文件异常，请确认url是否正确")
                            return
                        else:
                            # 下载成功，加载配置文件
                            redis.set(configFileRemoteUrlKey, p2)
                            if await loadConfigFile(configFilePath, context, True) != 0:
                                await context.edit(f"加载配置文件异常，请确认从远程下载的配置文件格式是否正确")
                                return
                            else:
                                await context.edit(f"下载并加载配置文件成功")
                    else:
                        # 没传url直接更新
                        if await updateConfig(configFilePath, context) != 0:
                            await context.edit(f"更新配置文件异常，请确认从远程下载的配置文件格式是否正确")
                            return
                        else:
                            await context.edit(f"从远程更新配置文件成功")
                    return
                elif p1[0] == "！" or p1[0] == "!":
                    # 加载配置
                    if exists(configFilePath):
                        if await loadConfigFile(configFilePath, context) != 0:
                            await context.edit(f"加载配置文件异常，请确认从远程下载的配置文件格式是否正确")
                            return
                    txt = ""
                    if len(positions) > 0:
                        for key in positions:
                            txt = f"{txt}，{key}"
                        if txt != "":
                            txt = txt[1:]
                    await context.edit(f"目前已有的模版列表如下：\n{txt}")
                    return
            defaultConfig = redis.get("shark.default-config")
            if isinstance(p2, str):
                number = p2
            elif isinstance(p2, int) and p2 > 0:
                number = int(p2)
            elif not diu_round and ((isinstance(p1, int) and int(p1) > 0) or isinstance(p1, str)):
                try:
                    number = int(p1)
                except:
                    number = p1
            elif defaultConfig:
                try:
                    defaultConfig = defaultConfig.decode()
                    number = int(defaultConfig)
                except:
                    number = str(defaultConfig)
        except:
            number = randint(1, max_number)

        # 加载配置
        if exists(configFilePath):
            if await loadConfigFile(configFilePath, context) != 0:
                await context.edit(f"加载配置文件异常，请确认从远程下载的配置文件格式是否正确")
                return

        try:
            notifyStr = notifyStrArr[str(number)]
        except:
            notifyStr = "🦈🦈"
        await context.edit(f"正在生成 {notifyStr} 图片中 . . .")
        markImg = Image.open("plugins/shark/" + str(target_user.user.id) + ".jpg")
        try:
            sharkImg = Image.open("plugins/shark/shark" + str(number) + ".png")
            maskImg = Image.open("plugins/shark/mask" + str(number) + ".png")
        except:
            await context.edit(f"图片模版加载出错，请检查并更新配置：{str(number)}")
            return

        if diu_round:
            markImg = markImg.rotate(180)  # 对图片进行旋转
        try:
            number = str(number)
        except:
            pass
        result = await shark_it(context, sharkImg, maskImg, markImg, number)
        result.save('plugins/shark/shark.webp')
        target_file = await context.client.upload_file("plugins/shark/shark.webp")
        try:
            remove("plugins/shark/" + str(target_user.user.id) + ".jpg")
            remove("plugins/shark/" + str(target_user.user.id) + ".png")
            remove("plugins/shark/" + str(from_user.user.id) + ".jpg")
            remove("plugins/shark/" + str(from_user.user.id) + ".png")
            remove("plugins/shark/shark.webp")
            remove(photo)
        except:
            pass
    else:
        await context.edit("此用户未设置头像或头像对您不可见。")
        return
    if reply_to:
        try:
            await context.client.send_file(
                context.chat_id,
                target_file,
                link_preview=False,
                force_document=False,
                reply_to=reply_to
            )
            await context.delete()
            remove("plugins/shark/shark.webp")
            try:
                remove(photo)
            except:
                pass
            return
        except TypeError:
            await context.edit("此用户未设置头像或头像对您不可见。")
        except ChatSendStickersForbiddenError:
            await context.edit("此群组无法发送贴纸。")
    else:
        try:
            await context.client.send_file(
                context.chat_id,
                target_file,
                link_preview=False,
                force_document=False
            )
            await context.delete()
            remove("plugins/shark/shark.webp")
            try:
                remove(photo)
            except:
                pass
            return
        except TypeError:
            await context.edit("此用户未设置头像或头像对您不可见。")
        except ChatSendStickersForbiddenError:
            await context.edit("此群组无法发送贴纸。")