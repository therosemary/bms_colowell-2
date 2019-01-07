# 锐翌医学管理系统

正式开发时间：2018/12/17   

fork之前请务必认真阅读[开发规范](https://github.com/gmdzy2010/bms_colowell/blob/master/specification_of_dev.md)，不符合此规范的任何pull request将被直接拒绝    

### 版本号
---------------
#### 功能框架
0.1.0 用户    

0.2.0 技术支持    
0.3.0 实验    
0.4.0 售后    

0.5.0 商务    
0.6.0 销售    
0.7.0 财务    
0.8.0 代理商   

#### 业务框架
0.9.0 产品分库    
0.10.0 用户分库    
0.11.0 OAuth2.0认证服务    
0.12.0 Redis高并发    

#### 正式发布
1.0.0 整个系统发布    


### 新增计划
-----------
#### `CAS系统`

1.Introduction    
>本项提供所有站点的web认证和授权服务    
>需要结合OAuth2.0认证系统    

2.Implementation
>CAS client: `django-cas-ng`  
>CAS server: `django-mama-cas`

#### `开发人员`

1.整体进度滞后1周，将不等待其他人员到位    

2.市场部UI人员已经问询开发进度    

3.本周五邮件通知各部门负责人目前进度

#### `注册/登陆流程设计`

1.如果要保持cas client与server端的用户信息同步，必须server端提供用户注册的接口，这样就能用户在子站点注册的同时，与server保持用户表同步