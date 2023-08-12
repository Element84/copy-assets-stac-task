## Instructions

This task copies specified Assets from Source STAC Item(s), uploads them to S3 and updates Item assets hrefs to point to the new location.

In order to run this task within Argo Workflows, follow the below instructions.

1. `cd` into this directory.

2. Create an image from the provided Dockerfile. If you are using Rancher Desktop to run your K8s cluster, you need to use `nerdctl` to build the image.

`nerdctl build --namespace k8s.io -t copyassets .`

This will create an image with the name & tag of `copyassets:latest`.

3. Make sure Argo Workflows is installed on the K8s cluster (see instructions [here](https://argoproj.github.io/argo-workflows/quick-start/)).

4. Upload the  `payload_workflow.json` file to object storage, such as S3. Change the `path_template` variable in `upload_options` to match a path where you want to save the output Item assets of this task. For example, if you want to save the output Item assets inside the `output` folder of a bucket named `copy_results` and templated by the Item's collection and id, the `path_template` would be `s3://copy_results/output/${collection}/${id}/`.

5. Make the bucket publically accessible and get the object URL associated with the uploaded payload in step 4.

6. Create a secret named `my-s3-credentials` that contains your AWS credentials. The secret must have the keys `access-key-id`, `secret-access-key`, and `session-token` for authenticating to AWS.

6. Run the Argo workflow in the same namespace where the Argo Workflow Controller is installed using:

`argo submit -n <NAMESPACE>--watch <FULL PATH TO WORKFLOW YAML FILE>`

substituting the appropriate values where needed.

You can either run the `workflow_copyassets_with_template.yaml` file or the `workflow_copyassets_no_template.yaml` file. If you run the `workflow_copyassets_with_template.yaml` file, you need to first have the Workflow Template installed. You can do this with `kubectl apply -n <NAMESPACE> -f <FULL PATH TO THE workflow-template.yaml file>` where `<NAMESPACE>` is the namespace where the Argo Workflow Controller is installed and the path is the full path to the workflow-template.yaml file.
