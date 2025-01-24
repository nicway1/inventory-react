from datetime import datetime

class InventoryItem:
    def __init__(self, id, asset_type, product, asset_tag, receiving_date, keyboard,
                 serial_num, po, model, erased, customer, condition, diag,
                 hardware_type, cpu_type, cpu_cores, gpu_cores, memory,
                 harddrive, charger, inventory, country):
        self.id = id
        self.asset_type = asset_type
        self.product = product
        self.asset_tag = asset_tag
        self.receiving_date = receiving_date
        self.keyboard = keyboard
        self.serial_num = serial_num
        self.po = po
        self.model = model
        self.erased = erased
        self.customer = customer
        self.condition = condition
        self.diag = diag
        self.hardware_type = hardware_type
        self.cpu_type = cpu_type
        self.cpu_cores = cpu_cores
        self.gpu_cores = gpu_cores
        self.memory = memory
        self.harddrive = harddrive
        self.charger = charger
        self.inventory = inventory
        self.country = country
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    @staticmethod
    def create(asset_type, product, asset_tag, receiving_date=None, keyboard=None,
              serial_num=None, po=None, model=None, erased=None, customer=None,
              condition=None, diag=None, hardware_type=None, cpu_type=None,
              cpu_cores=None, gpu_cores=None, memory=None, harddrive=None,
              charger=None, inventory=None, country=None):
        import random
        item_id = random.randint(1, 10000)
        return InventoryItem(
            id=item_id,
            asset_type=asset_type,
            product=product,
            asset_tag=asset_tag,
            receiving_date=receiving_date,
            keyboard=keyboard,
            serial_num=serial_num,
            po=po,
            model=model,
            erased=erased,
            customer=customer,
            condition=condition,
            diag=diag,
            hardware_type=hardware_type,
            cpu_type=cpu_type,
            cpu_cores=cpu_cores,
            gpu_cores=gpu_cores,
            memory=memory,
            harddrive=harddrive,
            charger=charger,
            inventory=inventory,
            country=country
        ) 