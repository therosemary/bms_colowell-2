import datetime
from django.utils.html import format_html
from django.contrib import admin
from django.db.models import Sum, Q
from import_export.admin import ImportExportActionModelAdmin
from daterange_filter.filter import DateRangeFilter
# from django.contrib.admin.views.main import ChangeList
from projects.models import InvoiceInfo
from invoices.models import SendInvoices, PaymentInfo
from invoices.forms import SendInvoicesForm
from invoices.resources import SendInvoiceResources, PaymentInfoResource


class PaymentInline(admin.TabularInline):
    model = PaymentInfo.send_invoice.through
    verbose_name = verbose_name_plural = "到账信息"
    extra = 1


class PaymentInfoAdmin(ImportExportActionModelAdmin):
    """到款信息管理"""

    # inlines = [PaymentInline]
    # exclude = ('send_invoice',)
    fields = (
        'receive_value', 'receive_date', 'contract_number', 'send_invoice'
    )
    list_display = (
        'payment_number', 'contract_number', 'receive_value', 'receive_date',
        'wait_invoices',
    )
    list_per_page = 30
    save_as_continue = False
    list_display_links = ('payment_number',)
    search_fields = ('payment_number',)
    resource_class = PaymentInfoResource

    def save_model(self, request, obj, form, change):
        receive_value = float(request.POST.get('receive_value', 0))
        if change:
            # 修改分两种情况，修改或及不修改发票信息
            send_invoice_id = [int(x) for x in
                               request.POST.getlist('send_invoice')]
            send_invoice_id.sort()
            before_send_invoice_data = obj.send_invoice.all().order_by('id')
            before_send_invoice_id = []
            if before_send_invoice_data is not None:
                for data in before_send_invoice_data:
                    before_send_invoice_id.append(data.id)
            # 求发票信息修改前后的差集
            diff_set = list(set(send_invoice_id) ^ set(before_send_invoice_id))
            if len(diff_set):
                # 发票信息有修改的情况，分为“”“”‘只新增’、‘只删除’、‘新增及删除’
                new_set = set(diff_set) ^ set(send_invoice_id)
                before_set = set(diff_set) ^ set(before_send_invoice_id)
                new_set_len = len(new_set)
                old_set_len = len(before_set)
                if new_set_len == 0 and old_set_len != 0:
                    # 只新增,获取新增开票信息
                    invoice_data = SendInvoices.objects.filter(id__in=diff_set)
                    invoice_data_order = invoice_data.order_by('fill_date')
                    print(invoice_data_order)
                    # 计算总应收金额
                    pay = invoice_data_order.aggregate(Sum('wait_payment'))
                    pay_sum = pay.get('wait_payment', 0)
                    print(pay_sum)
                    # 判断待到款额与总应收金额的大小
                    if receive_value >= pay_sum:
                        obj.wait_invoices = receive_value - pay_sum
                        try:
                            super(PaymentInfoAdmin, self).save_model(request,
                                                                     obj, form,
                                                                     change)
                            invoice_data.update(wait_payment=0)
                        except Exception:
                            pass
                    else:
                        obj.wait_payment = 0
                        super(PaymentInfoAdmin, self).save_model(request,
                                                                 obj, form,
                                                                 change)
                        if pay_sum - invoice_data[
                            -1].wait_payment < receive_value:
                            invoice_data[0:len(invoice_data) - 1].update(
                                wait_payment=0)
                            final_receive_value = pay_sum - receive_value
                            invoice_data[-1].update(
                                wait_payment=final_receive_value)
                        else:
                            pass
                elif new_set_len != 0 and old_set_len == 0:
                    # 只删除
                    pass
                elif new_set_len != 0 and old_set_len != 0:
                    # 新增及删除
                    pass
                pass
            else:
                super(PaymentInfoAdmin, self).save_model(request, obj, form,
                                                         change)
        else:
            # 新增
            if len(request.POST.getlist('send_invoice')):
                # 从request中获取关联的发票id并转为int类型
                send_invoice_id = [int(x) for x in
                                   request.POST.getlist('send_invoice')]
                print(send_invoice_id)
                # 从发票信息表中获取被选择中且应收额大于0的记录
                invoice_data = SendInvoices.objects.filter(
                    Q(id__in=send_invoice_id) & Q(wait_payment__gt=-1))
                # 按时间排序
                invoice_data_order = invoice_data.order_by('fill_date')
                print(invoice_data)
                pay = invoice_data_order.aggregate(
                    sum_payment=Sum('wait_payment'))
                pay_sum = pay.get('sum_payment', 0)
                print(pay_sum)
                temp = 'RE' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                obj.payment_number = temp
                if receive_value >= pay_sum:
                    # 到款额大于等于应收额
                    obj.wait_invoices = receive_value - pay_sum
                    try:
                        super(PaymentInfoAdmin, self).save_model(request, obj, form, change)
                        invoice_data.update(wait_payment=0)
                    except Exception:
                        pass
                else:
                    #到款额小于应收额，需确定最后一张发票的应收额
                    obj.wait_invoices = 0
                    super(PaymentInfoAdmin, self).save_model(request, obj, form, change)
                    # 判断是否多选发票，多选无任何意义
                    if pay_sum - invoice_data[-1].wait_payment < receive_value:
                        invoice_data[0:len(invoice_data)-1].update(wait_payment=0)
                        final_receive_value = pay_sum - receive_value
                        invoice_data[-1].update(wait_payment=final_receive_value)
                    else:
                        # TODO:提示错误信息:发票多选，无意义
                        pass
            else:
                #新增时不选择发票的情况
                obj.wait_invoices = receive_value
                if change:
                    super(PaymentInfoAdmin, self).save_model(request, obj, form, change)
                else:
                    temp = 'RE' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
                    obj.payment_number = temp
                    super(PaymentInfoAdmin, self).save_model(request, obj, form, change)


class SendInvoiceAdmin(ImportExportActionModelAdmin):
    """
    发票寄送信息管理
    注：每条记录在发票申请提交后自动被创建
    """
    # change_list_template = 'admin/invoices/change_list_template_invoices.html'
    inlines = [PaymentInline]
    change_list_template = 'admin/invoices/invoice_change_list.html'
    invoice_info = (
        'get_contract_number', 'get_invoice_type', 'get_invoice_issuing',
        'get_invoice_title', 'get_tariff_item',  'get_send_address',
        'get_address_phone', 'get_opening_bank', 'get_bank_account_number',
        'get_invoice_value', 'get_receive_value', 'get_receive_date',
    )
    send_invoice_info = (
        'invoice_number', 'billing_date', 'invoice_send_date',
        'tracking_number', 'ele_invoice', 'send_flag'
    )
    fieldsets = (
        ('发票申请信息', {
            'fields': invoice_info
        }),
        ('寄送信息填写', {
            'fields': send_invoice_info
        }),
    )
    list_display = (
        'get_salesman', 'get_contract_number', 'billing_date',
        'invoice_number', 'get_invoice_value', 'get_receive_value',
        'wait_payment', 'get_receive_date', 'get_invoice_title',
        'get_invoice_content', 'tracking_number', 'get_remark',
    )
    list_per_page = 40
    save_as_continue = False
    date_hierarchy = 'billing_date'
    readonly_fields = invoice_info
    form = SendInvoicesForm
    list_filter = (('invoice_id__fill_date', DateRangeFilter),
                   'invoice_id__salesman')
    resource_class = SendInvoiceResources
    list_display_links = ('get_salesman', 'get_contract_number')
    search_fields = ('invoice_number',)

    def receivables(self, obj):
        """自动计算应收金额"""
        invoice_value = self.get_invoice_value(obj)
        receive_value = self.get_receive_value(obj)
        if invoice_value is None:
            invoice_value = 0
        if receive_value is None:
            receive_value = 0
        money = invoice_value - receive_value
        return format_html('<span>{}</span>', money)
    receivables.short_description = "应收金额"

    def get_apply_name(self, obj):
        return obj.invoice_id.apply_name
    get_apply_name.short_description = "申请人"

    def get_salesman(self, obj):
        return obj.invoice_id.salesman
    get_salesman.short_description = "业务员"

    def get_contract_number(self, obj):
        invoice_data = InvoiceInfo.objects.get(id=obj.invoice_id.id)
        if invoice_data.contract_id is not None:
            return invoice_data.contract_id.contract_number
        else:
            return '-'
    get_contract_number.short_description = "合同号"

    def get_invoice_type(self, obj):
        return obj.invoice_id.invoice_type
    get_invoice_type.short_description = "发票类型"

    def get_invoice_issuing(self, obj):
        issuing_entities = {'shry': "上海锐翌", 'hzth': "杭州拓宏", 'hzry': "杭州锐翌",
                            'sdry': "山东锐翌"}
        return issuing_entities[obj.invoice_id.invoice_issuing]
    get_invoice_issuing.short_description = "开票单位"

    def get_invoice_title(self, obj):
        return obj.invoice_id.invoice_title
    get_invoice_title.short_description = "发票抬头"

    def get_tariff_item(self, obj):
        return obj.invoice_id.tariff_item
    get_tariff_item.short_description = "税号"

    def get_send_address(self, obj):
        return obj.invoice_id.send_address
    get_send_address.short_description = "对方地址"

    def get_address_phone(self, obj):
        return obj.invoice_id.address_phone
    get_address_phone.short_description = "电话"

    def get_opening_bank(self, obj):
        return obj.invoice_id.opening_bank
    get_opening_bank.short_description = "开户行"

    def get_bank_account_number(self, obj):
        return obj.invoice_id.bank_account_number
    get_bank_account_number.short_description = "账号"

    def get_invoice_value(self, obj):
        return obj.invoice_id.invoice_value
    get_invoice_value.short_description = "开票金额"

    def get_receive_date(self, obj):
        payment_date = None
        payment = obj.paymentinfo_set.exclude(receive_date__exact=None)
        payment_order = payment.order_by('-receive_date')
        if len(payment_order) > 0:
            payment_date = payment_order[0].receive_date
        return payment_date
    get_receive_date.short_description = "到账时间"

    def get_receive_value(self, obj):
        payment_sum = obj.invoice_id.invoice_value - obj.wait_payment
        return payment_sum
    get_receive_value.short_description = "到账金额"

    def get_invoice_content(self, obj):
        return obj.invoice_id.invoice_content
    get_invoice_content.short_description = "开票内容"

    def get_remark(self, obj):
        return obj.invoice_id.remark
    get_remark.short_description = "备注"

    @staticmethod
    def statistic_invoice_value(qs):
        """按时间段统计开票额及到款额"""
        invoice_values = 0
        receive_values = 0
        if qs is not None:
            for data in qs:
                invoice_data = InvoiceInfo.objects.get(id=data.invoice_id.id)
                if invoice_data.invoice_value is not None:
                    invoice_values += invoice_data.invoice_value
                payment_data = data.paymentinfo_set.exclude(receive_value__exact=None)
                if payment_data is not None:
                    for payment in payment_data:
                        receive_values += payment.receive_value
        return invoice_values, receive_values

    def get_readonly_fields(self, request, obj=None):
        # TODO: hasattr函数的隐含作用，在执行hasattr之前obj.name出现属性不存在错误
        # TODO：但执行后正常，为啥呢？
        self.readonly_fields = self.invoice_info
        # if obj:
        if hasattr(obj, 'send_flag'):
            if obj.send_flag:
                self.readonly_fields = self.invoice_info + self.send_invoice_info
        return self.readonly_fields

    def change_view(self, request, object_id, form_url='', extra_context=None):
        send_invoice = SendInvoices.objects.filter(pk=object_id)
        self.get_readonly_fields(request, obj=send_invoice)
        return super(SendInvoiceAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # TODO: 查询集换为按条件过滤后的
        # 筛选后的查询集由ListFilter中的queryset()返回，但不知如何获取
        # 发现template中的数据集由ChangeList类负责显示，显示集为调用get_results()
        # 函数后result_list的值，即筛选后的查询集
        result = self.get_changelist_instance(request)
        result.get_results(request)
        # print(request.META["QUERY"])
        # queryset = self.get_queryset()
        # query_string_dict = dict(request.META["QUERY"])
        # queryset.filter(invoice_id__gte=balald)
        # 获取model中的所有查询集
        # qs = super().get_queryset(request)
        qs = result.result_list
        extra_context['invoice_values'], extra_context['receive_values'] \
            = self.statistic_invoice_value(qs)
        return super(SendInvoiceAdmin, self).changelist_view(request, extra_context)

    # def get_changeform_initial_data(self, request):
    #     initial = super(SendInvoiceAdmin, self).get_changeform_initial_data(request)
    #     initial['fill_name'] = request.user
    #     return initial

    def save_model(self, request, obj, form, change):
        if change:
            obj.fill_name = request.user
        super(SendInvoiceAdmin, self).save_model(request, obj, form, change)
