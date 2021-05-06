import base64
import contextlib
import io
import json
import os.path as osp
import os
import chardet
import PIL.Image

from labelme import __version__
from labelme.logger import logger
from labelme import PY2
from labelme import QT4
from labelme import utils
from datetime import datetime
from utils.dateutil import DateEncoder


PIL.Image.MAX_IMAGE_PIXELS = None


@contextlib.contextmanager
def open(name, mode):
    assert mode in ["r", "w"]
    if PY2:
        mode += "b"
        encoding = None
    else:
        encoding = "utf-8"
    yield io.open(name, mode, encoding=encoding)
    return


class LabelFileError(Exception):
    pass

class LabelCocoFile(object):
    suffix = ".json"

    def __init__(self, foldername = None):
        self.annotations = []
        self.categories = []
        self.images = []
        self.info = []
        self.licenses = []
        if foldername is not None:
            self.foldername = foldername

    def load_json_file(self, folder):
        result = self.read_json_file(folder)

        data = dict()
        # info
        info = dict()
        info["contributor"] = ""
        info["date_created"] = datetime.now()
        info["description"] = ""
        info["url"] = ""
        info["version"] = "1"
        info["year"] = 2021
        # licenses
        licenses = []
        license_obj = dict()
        license_obj["id"] = 1
        license_obj["name"] = None
        license_obj["url"] = None
        licenses.append(license_obj)
        # images
        images = []
        image_id = 1
        label_set = set()
        label_id = 1
        for k in result:
            image_obj = dict()
            # image_obj["coco_url"] = ""
            # image_obj["date_captured"] = datetime.now()
            # image_obj["file_name"] = folder + "/" + k.get("imagePath")
            image_obj["file_name"] = k.get("imagePath")
            image_obj["height"] = k.get("imageHeight")
            image_obj["width"] = k.get("imageWidth")
            image_obj["id"] = image_id
            # image_obj["file"] = os.path.abspath(k.get("imagePath")) + "/" + k.get("imagePath")
            for root, dirname, filenames in os.walk(folder):
                for filename in filenames:
                    if filename == k.get("imagePath"):
                        path = os.path.join(root, filename).replace("\\", "/")
                        patharr = path.split("/")
                        foldername = folder.split("/")[-1]
                        pathname = "/".join(patharr[patharr.index(foldername):])
                        image_obj["file"] = pathname

            image_id += 1
            for i in k.get("shapes"):
                label_set.add(i.get("label"))
            images.append(image_obj)
            print(k , ' ----------- key -------')
        categories = []
        for m in label_set:
            category_obj = dict()
            category_obj["supercategory"] = "class"
            category_obj["id"] = label_id
            category_obj["name"] = m
            categories.append(category_obj)
            label_id += 1

        # annotation
        annotations = []
        annotation_id = 1
        for a in result:
            for b in a.get("shapes"):
                annotation_obj = dict()
                annotation_obj["segmentation"] = []
                annotation_obj["bbox"] = []
                annotation_obj["iscrowd"] = 0
                annotation_obj["id"] = annotation_id
                for k in categories:
                    if b.get("label") == k.get("name"):
                        annotation_obj["category_id"] = k.get("id")
                for j in images:
                    if a.get("imagePath") == j.get("file_name"):
                        annotation_obj["image_id"] = j.get("id")
                seg = []
                if len(b.get("points")) < 2:
                    print(a.get("imagePath"))
                if len(b.get("points")[0]) < 2:
                    print(a.get("imagePath"))
                if b.get("points")[0][0] < 0:
                    b.get("points")[0][0] = 0
                elif b.get("points")[0][1] < 0:
                    b.get("points")[0][1] = 0
                elif b.get("points")[1][0] < 0:
                    b.get("points")[1][0] = 0
                elif b.get("points")[1][1] < 0:
                    b.get("points")[1][1] = 0
                seg.append(b.get("points")[0][0])
                seg.append(b.get("points")[0][1])
                seg.append(b.get("points")[1][0])
                seg.append(b.get("points")[1][1] - b.get("points")[0][1])
                annotation_obj["segmentation"].append(seg)
                annotation_obj["bbox"].append(b.get("points")[0][0])
                annotation_obj["bbox"].append(b.get("points")[0][1])
                annotation_obj["bbox"].append(abs(b.get("points")[1][0] - b.get("points")[0][0]))
                annotation_obj["bbox"].append(abs(b.get("points")[1][1] - b.get("points")[0][1]))
                annotation_obj["area"] = abs(b.get("points")[1][0] - b.get("points")[0][0]) * abs(b.get("points")[1][1] - b.get("points")[0][1])
                annotation_id += 1
                annotations.append(annotation_obj)



        data["info"] = info
        data["licenses"] = licenses
        data["images"] = images
        data["categories"] = categories
        data["annotations"] = annotations


        with open(folder + "/coco.json", "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=DateEncoder)


    @staticmethod
    def read_json_file(foldername):
        datas = []
        for root, dirname, filelist in os.walk(foldername):
            for filename in filelist:
                with open(os.path.join(root, filename), "r") as f:
                    if f.name.split("/")[-1].split(".")[-1] == "json" and (f.name.split("/")[-1].split(".")[0] != "coco" and os.path.split(f.name)[-1].split(".")[0] != "coco"):
                        result = json.loads(f.read())
                        datas.append(result)
        return datas




class LabelFile(object):

    suffix = ".json"

    def __init__(self, filename=None):
        self.shapes = []
        self.imagePath = None
        self.imageData = None
        if filename is not None:
            self.load(filename)
        self.filename = filename

    @staticmethod
    def load_image_file(filename):
        try:
            image_pil = PIL.Image.open(filename)
        except IOError:
            logger.error("Failed opening image file: {}".format(filename))
            return

        # apply orientation to image according to exif
        image_pil = utils.apply_exif_orientation(image_pil)

        with io.BytesIO() as f:
            ext = osp.splitext(filename)[1].lower()
            if PY2 and QT4:
                format = "PNG"
            elif ext in [".jpg", ".jpeg"]:
                format = "JPEG"
            else:
                format = "PNG"
            image_pil.save(f, format=format)
            f.seek(0)
            return f.read()

    def load(self, filename):
        keys = [
            "version",
            "imageData",
            "imagePath",
            "shapes",  # polygonal annotations
            "flags",  # image level flags
            "imageHeight",
            "imageWidth",
        ]
        shape_keys = [
            "label",
            "points",
            "group_id",
            "shape_type",
            "flags",
        ]
        try:
            with open(filename, "r") as f:
                data = json.load(f)
            version = data.get("version")
            if version is None:
                logger.warn(
                    "Loading JSON file ({}) of unknown version".format(
                        filename
                    )
                )
            elif version.split(".")[0] != __version__.split(".")[0]:
                logger.warn(
                    "This JSON file ({}) may be incompatible with "
                    "current labelme. version in file: {}, "
                    "current version: {}".format(
                        filename, version, __version__
                    )
                )

            if data["imageData"] is not None:
                imageData = base64.b64decode(data["imageData"])
                if PY2 and QT4:
                    imageData = utils.img_data_to_png_data(imageData)
            else:
                # relative path from label file to relative path from cwd
                imagePath = osp.join(osp.dirname(filename), data["imagePath"])
                imageData = self.load_image_file(imagePath)
            flags = data.get("flags") or {}
            imagePath = data["imagePath"]
            self._check_image_height_and_width(
                base64.b64encode(imageData).decode("utf-8"),
                data.get("imageHeight"),
                data.get("imageWidth"),
            )
            shapes = [
                dict(
                    label=s["label"],
                    points=s["points"],
                    shape_type=s.get("shape_type", "polygon"),
                    flags=s.get("flags", {}),
                    group_id=s.get("group_id"),
                    other_data={
                        k: v for k, v in s.items() if k not in shape_keys
                    },
                )
                for s in data["shapes"]
            ]
        except Exception as e:
            raise LabelFileError(e)

        otherData = {}
        for key, value in data.items():
            if key not in keys:
                otherData[key] = value

        # Only replace data after everything is loaded.
        self.flags = flags
        self.shapes = shapes
        self.imagePath = imagePath
        self.imageData = imageData
        self.filename = filename
        self.otherData = otherData

    @staticmethod
    def _check_image_height_and_width(imageData, imageHeight, imageWidth):
        img_arr = utils.img_b64_to_arr(imageData)
        if imageHeight is not None and img_arr.shape[0] != imageHeight:
            logger.error(
                "imageHeight does not match with imageData or imagePath, "
                "so getting imageHeight from actual image."
            )
            imageHeight = img_arr.shape[0]
        if imageWidth is not None and img_arr.shape[1] != imageWidth:
            logger.error(
                "imageWidth does not match with imageData or imagePath, "
                "so getting imageWidth from actual image."
            )
            imageWidth = img_arr.shape[1]
        return imageHeight, imageWidth

    def save(
        self,
        filename,
        shapes,
        imagePath,
        imageHeight,
        imageWidth,
        imageData=None,
        otherData=None,
        flags=None,
    ):
        if imageData is not None:
            imageData = base64.b64encode(imageData).decode("utf-8")
            imageHeight, imageWidth = self._check_image_height_and_width(
                imageData, imageHeight, imageWidth
            )
        if otherData is None:
            otherData = {}
        if flags is None:
            flags = {}
        data = dict(
            version=__version__,
            flags=flags,
            shapes=shapes,
            imagePath=imagePath,
            # imageData=imageData,
            imageData=None,
            imageHeight=imageHeight,
            imageWidth=imageWidth,
        )
        for key, value in otherData.items():
            assert key not in data
            data[key] = value
        try:
            with open(filename, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.filename = filename
        except Exception as e:
            raise LabelFileError(e)

    @staticmethod
    def is_label_file(filename):
        return osp.splitext(filename)[1].lower() == LabelFile.suffix
