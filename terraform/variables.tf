variable "project_id" {                                                                                   
description = "GCP Project ID"                                                                          
type        = string        
default = "clickstream-pipeline-484705"                                                                         
}                                                                                                         
                                                                                                        
variable "region" {                                                                                       
description = "GCP Region"                                                                              
type        = string                                                                                    
default     = "asia-northeast3"                                                                             
}                                                                                                         
                                                                                                        
variable "location" {                                                                                     
description = "GCS/BigQuery location"                                                                   
type        = string                                                                                    
default     = "asia-northeast3"                                                                                      
}       


variable "dataset_id" {                                                                                     
description = "gcs dataset_id"                                                                   
type        = string                                                                                    
default     = "clickstream"                                                                                      
} 
                                     