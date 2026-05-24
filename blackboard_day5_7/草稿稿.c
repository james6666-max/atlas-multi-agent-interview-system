#include <stdio.h>
#include <stdlib.h>

typedef struct{
    int row[4];
    int sum;
}Line;


int cmp(const void*a,const void b){
    Line*x=(Line*)a;
    Line*y=(Line*)b;
    return x->sum-y->sum;
}


void line_sort(int a[][4],int b[],int n){
    Line c[5];
    int i,j;
    for(int i=0;i<n;i++){
        c[i].sum=0;
        for(j=0;j<4;j++){
            c[i].row[j]=a[i][j];
            c[i].sum+=a[i][j];
        }
    }

    qsort(c,n,sizeof(Line),cmp);

    for(i=0;i<n;i++){
        b[i]=c[i].sum;
        for(j=0;j<4;j++){
            a[i][j]=c[i].row[j];
        }
    }
}

int main() {
    int a[5][4];
    int b[5];
    int i, j;

    for (i = 0; i < 5; i++) {
        for (j = 0; j < 4; j++) {
            scanf("%d", &a[i][j]);
        }
    }

    line_sort(a, b, 5);

    for (i = 0; i < 5; i++) {
        for (j = 0; j < 4; j++) {
            printf("%d ", a[i][j]);
        }
        printf("\n");
    }

    printf("sum\n");

    for (i = 0; i < 5; i++) {
        printf("%d ", b[i]);
    }

    return 0;
}