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


positions = {
    "1": [301, 24]
}
max_number = 1


def eat_it(base, mask, photo, number):
    mask = mask.resize((184, 184), Image.LANCZOS)
    mask_size = mask.size
    photo_size = photo.size
    if mask_size[0] < photo_size[0] and mask_size[1] < photo_size[1]:
        scale = photo_size[1] / mask_size[1]
        photo = photo.resize(
            (int(photo_size[0] / scale), int(photo_size[1] / scale)), Image.LANCZOS)
    photo = photo.crop((0, 0, mask_size[0], mask_size[1]))
    mask1 = Image.new('RGBA', mask_size)
    mask1.paste(photo, mask=mask)
    base.paste(mask1, (positions[str(number)][0],
               positions[str(number)][1]), mask1)
    temp = base.size[0] if base.size[0] > base.size[1] else base.size[1]
    if temp != 512:
        scale = 512 / temp
        base = base.resize(
            (int(base.size[0] * scale), int(base.size[1] * scale)), Image.LANCZOS)
    return base


@listener(is_plugin=True, outgoing=True, command=alias_command("hit"),
          description="生成一张 踢人图片，（可选：当第二个参数存在时，旋转用户头像 180°）",
          parameters="<username/uid> [随意内容]")
async def turn(context):
    if len(context.parameter) > 2:
        await context.edit("出错了呜呜呜 ~ 无效的参数。")
        return
    diu_round = False
    await context.edit("正在生成 踢人 图片中 . . .")
    if context.reply_to_msg_id:
        reply_message = await context.get_reply_message()
        try:
            user_id = reply_message.sender_id
        except AttributeError:
            await context.edit("出错了呜呜呜 ~ 无效的参数。")
            return
        target_user = await context.client(GetFullUserRequest(user_id))
        if len(context.parameter) == 1:
            diu_round = True
    else:
        if len(context.parameter) == 1 or len(context.parameter) == 2:
            user = context.parameter[0]
            if user.isnumeric():
                user = int(user)
        else:
            user_object = await context.client.get_me()
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
        "plugins/turn/" + str(target_user.user.id) + ".jpg",
        download_big=True
    )
    reply_to = context.message.reply_to_msg_id
    if exists("plugins/turn/" + str(target_user.user.id) + ".jpg"):
        for num in range(1, max_number + 1):
            print(num)
            if not exists('plugins/turn/turn' + str(num) + '.png'):
                re = get(
                    'https://raw.githubusercontent.com/fishingworld/PagerMaid_Plugins/master/turn/hit' + str(num) + '.png')
                with open('plugins/turn/turn' + str(num) + '.png', 'wb') as bg:
                    bg.write(re.content)
            if not exists('plugins/turn/mask' + str(num) + '.png'):
                re = get(
                    'https://raw.githubusercontent.com/FlowerSilent/Photo/master/photo/mask3.png')
                with open('plugins/turn/mask' + str(num) + '.png', 'wb') as ms:
                    ms.write(re.content)
        number = randint(1, max_number)
        markImg = Image.open(
            "plugins/turn/" + str(target_user.user.id) + ".jpg")
        eatImg = Image.open("plugins/turn/turn" + str(number) + ".png")
        maskImg = Image.open("plugins/turn/mask" + str(number) + ".png")
        if len(context.parameter) == 2:
            diu_round = True
        if diu_round:
            markImg = markImg.rotate(180)  # 对图片进行旋转
        await context.edit(f"绿幕尺寸：{maskImg.size}")
        await context.edit(f"头像尺寸：{markImg.size}")
        try:
            result = eat_it(eatImg, maskImg, markImg, number)
        except Exception as e:
            await context.edit(f"错误：{e}")
        result.save('plugins/turn/turn.webp')
        target_file = await context.client.upload_file("plugins/turn/turn.webp")
        try:
            remove("plugins/turn/" + str(target_user.user.id) + ".jpg")
            remove("plugins/turn/" + str(target_user.user.id) + ".png")
            remove("plugins/turn/turn.webp")
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
            remove("plugins/turn/turn.webp")
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
            remove("plugins/turn/turn.webp")
            try:
                remove(photo)
            except:
                pass
            return
        except TypeError:
            await context.edit("此用户未设置头像或头像对您不可见。")
        except ChatSendStickersForbiddenError:
            await context.edit("此群组无法发送贴纸。")
