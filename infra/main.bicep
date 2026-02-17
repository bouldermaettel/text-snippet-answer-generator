// Azure Container Apps deployment for RAG Snippet Answer Generator
// Deploy: az deployment group create -g <rg> --template-file infra/main.bicep --parameters infra/parameters.json
//
// NOTE: Persistent storage (Azure File Share) is commented out because the
// organization policy denies storage accounts with shared key access, which
// Container Apps requires for Azure File mounts. An ephemeral EmptyDir volume
// is used instead. Data persists across container restarts but is lost on new
// revisions or scale events. To enable persistent storage, request a policy
// exemption and uncomment the Storage Account / File Share / envStorage
// sections, then switch the volume from EmptyDir to AzureFile.

@description('Base name for all resources')
param appName string = 'snippet-answer'

@description('Azure region')
param location string = resourceGroup().location

@description('Container image (full ACR path, e.g. myacr.azurecr.io/snippet-answer:latest)')
param containerImage string

@description('JWT secret for authentication')
@secure()
param jwtSecret string

@description('Azure OpenAI endpoint URL')
param azureOpenAiEndpoint string = ''

@description('Azure OpenAI API key')
@secure()
param azureOpenAiApiKey string = ''

@description('Azure OpenAI chat deployment name')
param azureOpenAiChatDeployment string = 'gpt-4-32k'

@description('Azure OpenAI embedding deployment name')
param azureOpenAiEmbeddingDeployment string = 'text-embedding-3-small'

@description('Azure OpenAI API version')
param azureOpenAiApiVersion string = '2024-12-01-preview'

@description('Initial admin email for seeding')
param adminEmail string = ''

@description('Initial admin password')
@secure()
param adminPassword string = ''

@description('Container App CPU cores')
param cpuCores string = '1.0'

@description('Container App memory')
param memorySize string = '2Gi'

// ---------------------------------------------------------------------------
// Log Analytics Workspace
// ---------------------------------------------------------------------------
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------------
// Container Registry
// ---------------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('${appName}acr', '-', '')
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ---------------------------------------------------------------------------
// Storage Account + File Share (persistent volume for data/)
// DISABLED: Organization policy denies shared key access on storage accounts.
// Container Apps Azure File mounts require shared keys.
// Uncomment once a policy exemption is granted.
// ---------------------------------------------------------------------------
// resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
//   name: replace('${appName}store', '-', '')
//   location: location
//   sku: {
//     name: 'Standard_LRS'
//   }
//   kind: 'StorageV2'
// }
//
// resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
//   parent: storageAccount
//   name: 'default'
// }
//
// resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
//   parent: fileService
//   name: '${appName}-data'
//   properties: {
//     shareQuota: 5
//   }
// }

// ---------------------------------------------------------------------------
// Container Apps Environment
// ---------------------------------------------------------------------------
resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Uncomment once storage account policy exemption is granted:
// resource envStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
//   parent: containerEnv
//   name: 'data-volume'
//   properties: {
//     azureFile: {
//       accountName: storageAccount.name
//       accountKey: storageAccount.listKeys().keys[0].value
//       shareName: fileShare.name
//       accessMode: 'ReadWrite'
//     }
//   }
// }

// ---------------------------------------------------------------------------
// Container App
// ---------------------------------------------------------------------------
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'jwt-secret'
          value: jwtSecret
        }
        {
          name: 'azure-openai-api-key'
          value: azureOpenAiApiKey
        }
        {
          name: 'admin-password'
          value: adminPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: appName
          image: containerImage
          resources: {
            cpu: json(cpuCores)
            memory: memorySize
          }
          env: [
            {
              name: 'ENVIRONMENT'
              value: 'production'
            }
            {
              name: 'PORT'
              value: '8000'
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'jwt-secret'
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAiEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-api-key'
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: azureOpenAiChatDeployment
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: azureOpenAiEmbeddingDeployment
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: azureOpenAiApiVersion
            }
            {
              name: 'ADMIN_EMAIL'
              value: adminEmail
            }
            {
              name: 'ADMIN_PASSWORD'
              secretRef: 'admin-password'
            }
            {
              name: 'CHROMA_PERSIST_DIR'
              value: '/app/data/chroma'
            }
            {
              name: 'DATABASE_URL'
              value: '/app/data/users.db'
            }
            {
              name: 'UPLOAD_DIR'
              value: '/app/data/uploads'
            }
            {
              name: 'ALLOWED_ORIGINS'
              value: ''
            }
            {
              name: 'LLM_PROVIDER'
              value: 'azure'
            }
            {
              name: 'LOG_LEVEL'
              value: 'INFO'
            }
          ]
          volumeMounts: [
            {
              volumeName: 'data'
              mountPath: '/app/data'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/ready'
                port: 8000
              }
              initialDelaySeconds: 15
              periodSeconds: 10
            }
            {
              type: 'Startup'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 5
              failureThreshold: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
      volumes: [
        {
          name: 'data'
          storageType: 'EmptyDir'
        }
      ]
    }
  }
}

// ---------------------------------------------------------------------------
// Outputs
// ---------------------------------------------------------------------------
output appUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
