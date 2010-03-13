#include "graphserver.h"

// LIST FUNCTIONS

ListNode*
liNew(Edge *data) {
    ListNode *ret = (ListNode*)malloc(sizeof(ListNode));
    ret->data = data;
    ret->next = NULL;
    return ret;
}

void
liInsertAfter( ListNode *this, ListNode* add ) {
    add->next = this->next;
    this->next = add;
}

void
liRemoveAfter( ListNode *this ) {
    if( this->next ) {
      ListNode* condemned = this->next;
      this->next = this->next->next;
      free( condemned );
    }
}

void
liRemoveRef( ListNode *dummyhead, Edge *data ) {
    ListNode* prev = dummyhead;
    ListNode* curr = dummyhead->next;

    while(curr) {
      if(curr->data == data) {
        liRemoveAfter( prev );
        break;
      }
      prev = curr;
      curr = prev->next;
    }
}

Edge*
liGetData( ListNode *this ) {
	return this->data;
}

ListNode*
liGetNext( ListNode *this ) {
	return this->next;
}
